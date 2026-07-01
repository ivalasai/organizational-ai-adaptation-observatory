"""SEC EDGAR HTTP client for public, credential-free access."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from oaa_observatory.utils.logging import logger

SEC_BASE = "https://www.sec.gov"
DATA_BASE = "https://data.sec.gov"
COMPANY_TICKERS_URL = f"{SEC_BASE}/files/company_tickers.json"
DEFAULT_USER_AGENT = "OAA-Observatory indarsvalasai@gmail.com"


class SECClient:
    """Thin client for SEC EDGAR public APIs.

    Respects SEC fair-access guidance: identifiable User-Agent and modest rate limits.
    No API keys or WRDS credentials are used.
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        requests_per_second: float = 8.0,
    ) -> None:
        """Initialize SEC client.

        Args:
            user_agent: Required SEC User-Agent string (name + email).
            requests_per_second: Maximum sustained request rate.
        """
        self.user_agent = user_agent
        self._min_interval = 1.0 / requests_per_second
        self._last_request = 0.0
        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=60.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> SECClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    def get_json(self, url: str) -> Any:
        """Fetch and parse a JSON response."""
        self._throttle()
        response = self._client.get(url)
        response.raise_for_status()
        return response.json()

    def get_text(self, url: str) -> str:
        """Fetch response body as text."""
        self._throttle()
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def get_bytes(self, url: str) -> bytes:
        """Fetch response body as bytes."""
        self._throttle()
        response = self._client.get(url)
        response.raise_for_status()
        return response.content

    def fetch_company_tickers(self) -> dict[str, dict[str, Any]]:
        """Download SEC ``company_tickers.json`` mapping."""
        logger.info("Fetching SEC company_tickers.json")
        raw = self.get_json(COMPANY_TICKERS_URL)
        by_ticker: dict[str, dict[str, Any]] = {}
        for entry in raw.values():
            ticker = str(entry["ticker"]).upper()
            by_ticker[ticker] = {
                "cik": str(entry["cik_str"]).zfill(10),
                "title": entry["title"],
            }
        return by_ticker

    def fetch_submissions(self, cik: str) -> dict[str, Any]:
        """Fetch EDGAR submissions JSON for a CIK."""
        cik_padded = str(int(cik)).zfill(10)
        url = f"{DATA_BASE}/submissions/CIK{cik_padded}.json"
        return dict(self.get_json(url))

    def iter_all_filings(self, cik: str) -> list[dict[str, str]]:
        """Return all filing records for a CIK across paginated submission files."""
        submissions = self.fetch_submissions(cik)
        filings = submissions.get("filings", {})
        records = self._parse_filing_batch(filings.get("recent", {}))

        for file_meta in filings.get("files", []):
            name = file_meta["name"]
            url = urljoin(f"{DATA_BASE}/submissions/", name)
            extra = self.get_json(url)
            records.extend(self._parse_filing_batch(extra))

        return records

    @staticmethod
    def _parse_filing_batch(batch: dict[str, Any]) -> list[dict[str, str]]:
        if not batch:
            return []
        keys = batch.keys()
        n = len(batch.get("accessionNumber", []))
        rows: list[dict[str, str]] = []
        for i in range(n):
            rows.append({k: batch[k][i] for k in keys})
        return rows

    def filing_document_url(self, cik: str, accession: str, primary_document: str) -> str:
        """Build the URL for a primary filing document."""
        cik_int = str(int(cik))
        accession_nodash = accession.replace("-", "")
        return f"{SEC_BASE}/Archives/edgar/data/{cik_int}/{accession_nodash}/{primary_document}"

    def download_filing(
        self,
        cik: str,
        accession: str,
        primary_document: str,
        dest: Path,
    ) -> Path:
        """Download a filing document if not already present.

        Args:
            cik: SEC CIK.
            accession: Accession number with dashes.
            primary_document: Primary document filename.
            dest: Destination file path.

        Returns:
            Path to the downloaded (or existing) file.
        """
        if dest.exists():
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = self.filing_document_url(cik, accession, primary_document)
        content = self.get_bytes(url)
        dest.write_bytes(content)
        return dest
