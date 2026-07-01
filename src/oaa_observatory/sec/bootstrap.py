"""Bootstrap entity resolution from SEC public ticker file and firm universe."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.entity_resolution import EntityResolver
from oaa_observatory.schemas.records import FirmIdentifier
from oaa_observatory.sec.client import SECClient
from oaa_observatory.utils.logging import logger


def load_firm_universe(path: Path) -> pd.DataFrame:
    """Load the static firm universe CSV (skips ``#`` comment lines)."""
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    from io import StringIO

    return pd.read_csv(StringIO("\n".join(lines)))


def bootstrap_entity_resolution(
    universe_path: Path,
    mapping_path: Path,
    user_agent: str,
) -> EntityResolver:
    """Map universe tickers to CIKs via SEC ``company_tickers.json``.

    GVKEY and PERMNO are left null. Unmatched tickers are logged and skipped.

    Args:
        universe_path: Path to static firm universe CSV.
        mapping_path: Path to write entity resolution Parquet mapping.
        user_agent: SEC User-Agent string.

    Returns:
        Populated EntityResolver.
    """
    universe = load_firm_universe(universe_path)
    resolver = EntityResolver()

    with SECClient(user_agent=user_agent) as client:
        ticker_map = client.fetch_company_tickers()

    matched = 0
    for _, row in universe.iterrows():
        ticker = str(row["ticker"]).upper()
        meta = ticker_map.get(ticker)
        if meta is None:
            logger.warning("No SEC CIK found for ticker {}", ticker)
            continue
        record = FirmIdentifier(
            firm_id="",
            gvkey=None,
            cik=meta["cik"],
            ticker=ticker,
            cusip=None,
            permno=None,
            company_name=str(row.get("company_name", meta.get("title", ""))),
            source="sec_company_tickers",
        )
        resolver.register(record)
        matched += 1

    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    resolver.save(mapping_path)
    logger.info("Bootstrapped {}/{} firms to {}", matched, len(universe), mapping_path)
    return resolver
