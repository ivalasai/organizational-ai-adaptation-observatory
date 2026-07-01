"""SEC EDGAR 10-K / 10-Q attention signal pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd

from oaa_observatory.config.loader import load_config
from oaa_observatory.config.models import SECConfig
from oaa_observatory.config.settings import Settings
from oaa_observatory.entity_resolution import EntityResolver
from oaa_observatory.ingestion.base import BasePipeline
from oaa_observatory.nlp.keyword_counter import KeywordCounter
from oaa_observatory.sec.bootstrap import bootstrap_entity_resolution, load_firm_universe
from oaa_observatory.sec.client import SECClient
from oaa_observatory.sec.parser import parse_filing_bytes
from oaa_observatory.utils.logging import logger


def _year_from_accession(accession: str) -> int:
    """Infer calendar year from SEC accession number."""
    parts = accession.split("-")
    if len(parts) >= 2 and parts[1].isdigit():
        yy = int(parts[1])
        return 2000 + yy if yy < 70 else 1900 + yy
    return 2015


def _normalize_manifest_cik(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).split(".")[0]
    return str(int(text)).zfill(10)


class SECFilingsPipeline(BasePipeline):
    """Download and process SEC 10-K/10-Q filings for the fixed firm universe.

    Produces firm-year attention counts via the keyword counter.
    Raw filings are stored once under ``data/raw/sec/`` and never overwritten.
    """

    def __init__(
        self,
        config: SECConfig | None = None,
        settings: Settings | None = None,
        universe_path: Path | None = None,
    ) -> None:
        """Initialize SEC pipeline."""
        cfg = config or SECConfig()
        super().__init__(cfg, settings)
        self._config: SECConfig = self.config  # type: ignore[assignment]
        self.universe_path = universe_path or self._config.universe_path
        self.mapping_path = Path("data/intermediate/entity_resolution/mappings.parquet")
        self._keyword_counter = KeywordCounter(self._config.ai_keywords)
        self._manifest_path = self.raw_path / "download_manifest.parquet"

    @classmethod
    def from_config_file(cls, path: Path | str) -> SECFilingsPipeline:
        """Create pipeline from a TOML config file."""
        raw = load_config(path)
        config = SECConfig.model_validate(raw)
        return cls(config=config)

    def _filing_path(self, cik: str, accession: str, primary_document: str) -> Path:
        """Resolve on-disk path for a filing (SEC uses unpadded CIK in paths)."""
        cik_dir = str(int(str(cik)))
        return self.raw_path / cik_dir / accession.replace("-", "") / primary_document

    def bootstrap_identifiers(self) -> EntityResolver:
        """Populate entity resolution from SEC company_tickers.json."""
        return bootstrap_entity_resolution(
            universe_path=self.universe_path,
            mapping_path=self.mapping_path,
            user_agent=self.settings.sec_user_agent,
        )

    def ingest(self) -> Path:
        """Download 10-K and 10-Q filings for the firm universe (skip existing)."""
        self.raw_path.mkdir(parents=True, exist_ok=True)
        resolver = self.bootstrap_identifiers()
        universe = load_firm_universe(self.universe_path)

        manifest_rows: list[dict[str, object]] = []
        if self._manifest_path.exists():
            existing = cast(
                list[dict[str, object]],
                pd.read_parquet(self._manifest_path).to_dict("records"),
            )
            manifest_rows = existing

        existing_keys = {
            (str(r["cik"]), str(r["accession_number"]))
            for r in manifest_rows
            if "cik" in r and "accession_number" in r
        }

        start_year = self._config.start_year
        end_year = self._config.end_year or datetime.now().year
        allowed_forms = set(self._config.filing_types)

        with SECClient(user_agent=self.settings.sec_user_agent) as client:
            for _, row in universe.iterrows():
                ticker = str(row["ticker"]).upper()
                firm_id = resolver.resolve("ticker", ticker)
                if firm_id is None:
                    continue
                mapping = resolver.mapping_table
                match = mapping[mapping["ticker"] == ticker]
                if match.empty:
                    continue
                cik = str(match.iloc[0]["cik"])

                try:
                    filings = client.iter_all_filings(cik)
                except Exception as exc:
                    logger.warning("Failed submissions for {} ({}): {}", ticker, cik, exc)
                    continue

                for filing in filings:
                    form = filing.get("form", "")
                    if form not in allowed_forms:
                        continue
                    filing_date = filing.get("filingDate", "")
                    if not filing_date:
                        continue
                    year = int(filing_date[:4])
                    if year < start_year or year > end_year:
                        continue

                    accession = filing.get("accessionNumber", "")
                    primary = filing.get("primaryDocument", "")
                    if not accession or not primary:
                        continue

                    key = (cik, accession)
                    if key in existing_keys:
                        continue

                    dest = self._filing_path(cik, accession, primary)
                    try:
                        client.download_filing(cik, accession, primary, dest)
                    except Exception as exc:
                        logger.warning("Download failed {} {}: {}", ticker, accession, exc)
                        continue

                    manifest_rows.append(
                        {
                            "firm_id": firm_id,
                            "ticker": ticker,
                            "cik": str(cik).zfill(10),
                            "accession_number": accession,
                            "form_type": form,
                            "filing_date": filing_date,
                            "fiscal_year": year,
                            "primary_document": primary,
                            "raw_path": str(dest.resolve()),
                        }
                    )
                    existing_keys.add(key)
                    logger.info("Downloaded {} {} ({})", ticker, form, accession)

        manifest = pd.DataFrame(manifest_rows)
        if not manifest.empty:
            manifest["cik"] = manifest["cik"].map(_normalize_manifest_cik)
            self.write_stage_output(manifest, self._manifest_path, stage="raw")
        return self.raw_path

    def standardize(self) -> Path:
        """Parse raw filings to document-level plain text records."""
        output = self.intermediate_path / "documents.parquet"
        self.intermediate_path.mkdir(parents=True, exist_ok=True)

        if not self._manifest_path.exists():
            logger.warning("No download manifest; writing empty intermediate table")
            return self.write_stage_output(
                pd.DataFrame(
                    columns=[
                        "document_id",
                        "firm_id",
                        "cik",
                        "ticker",
                        "form_type",
                        "filing_date",
                        "fiscal_year",
                        "text",
                        "raw_path",
                    ]
                ),
                output,
                stage="intermediate",
            )

        manifest = pd.read_parquet(self._manifest_path)
        manifest["cik"] = manifest["cik"].map(_normalize_manifest_cik)
        records: list[dict[str, object]] = []
        total = len(manifest)

        for i, (_, row) in enumerate(manifest.iterrows()):
            if i and i % 500 == 0:
                logger.info("Parsing filing {}/{}", i, total)
            raw_path = self._filing_path(
                str(row["cik"]),
                str(row["accession_number"]),
                str(row["primary_document"]),
            )
            if not raw_path.exists():
                stored = Path(str(row.get("raw_path", "")))
                raw_path = stored if stored.exists() else raw_path
            if not raw_path.exists():
                continue
            text = parse_filing_bytes(raw_path.read_bytes())
            doc_id = f"{row['cik']}_{row['accession_number']}_{row['primary_document']}"
            fiscal_year = row.get("fiscal_year")
            if pd.isna(fiscal_year) or int(fiscal_year) == 0:
                filing_date = str(row.get("filing_date", ""))
                if filing_date[:4].isdigit():
                    fiscal_year = int(filing_date[:4])
                else:
                    fiscal_year = _year_from_accession(str(row["accession_number"]))
            records.append(
                {
                    "document_id": doc_id,
                    "firm_id": row["firm_id"],
                    "cik": row["cik"],
                    "ticker": row["ticker"],
                    "form_type": row["form_type"],
                    "filing_date": row["filing_date"],
                    "fiscal_year": int(fiscal_year),
                    "text": text,
                    "raw_path": str(raw_path),
                }
            )

        df = pd.DataFrame(records)
        return self.write_stage_output(df, output, stage="intermediate")

    def extract_features(self) -> Path:
        """Aggregate document-level AI mentions to firm-year attention signals."""
        intermediate = self.intermediate_path / "documents.parquet"
        output = self.features_path / "firm_year.parquet"
        self.features_path.mkdir(parents=True, exist_ok=True)

        if not intermediate.exists():
            df = pd.DataFrame(
                columns=[
                    "firm_id",
                    "year",
                    "source",
                    "document_count",
                    "ai_mention_count",
                    "ai_mention_share",
                    "total_tokens",
                    "ai_token_count",
                ]
            )
            return self.write_stage_output(df, output, stage="features")

        documents = pd.read_parquet(intermediate)
        if documents.empty:
            return self.write_stage_output(
                pd.DataFrame(
                    columns=[
                        "firm_id",
                        "year",
                        "source",
                        "document_count",
                        "ai_mention_count",
                        "ai_mention_share",
                        "total_tokens",
                        "ai_token_count",
                    ]
                ),
                output,
                stage="features",
            )

        doc_features: list[dict[str, object]] = []
        for _, row in documents.iterrows():
            counts = self._keyword_counter.count(str(row.get("text", "")))
            doc_features.append(
                {
                    "document_id": row["document_id"],
                    "firm_id": row["firm_id"],
                    "year": row["fiscal_year"],
                    "ai_mention_count": counts.mention_count,
                    "total_tokens": counts.total_tokens,
                    "ai_token_count": counts.keyword_token_count,
                    "has_ai_mention": counts.mention_count > 0,
                }
            )

        doc_df = pd.DataFrame(doc_features)
        aggregated = (
            doc_df.groupby(["firm_id", "year"], dropna=False)
            .agg(
                document_count=("document_id", "count"),
                ai_mention_count=("ai_mention_count", "sum"),
                total_tokens=("total_tokens", "sum"),
                ai_token_count=("ai_token_count", "sum"),
                ai_document_count=("has_ai_mention", "sum"),
            )
            .reset_index()
        )
        aggregated["ai_mention_share"] = aggregated["ai_document_count"] / aggregated[
            "document_count"
        ].clip(lower=1)
        aggregated["source"] = self._config.name
        features = aggregated.drop(columns=["ai_document_count"])
        return self.write_stage_output(features, output, stage="features")
