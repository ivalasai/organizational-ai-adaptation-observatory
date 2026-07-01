#!/usr/bin/env python3
"""One-time script to build the static firm universe CSV from Wikipedia."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import httpx
import pandas as pd

OUTPUT = Path("data/universe/firm_universe.csv")
PILOT_SIZE = 100
SOURCE_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
USER_AGENT = "OAA-Observatory indarsvalasai@gmail.com (research; firm universe build)"


def main() -> None:
    response = httpx.get(SOURCE_URL, headers={"User-Agent": USER_AGENT}, timeout=60.0)
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text))
    sp500 = tables[0]
    sp500 = sp500.rename(
        columns={
            "Symbol": "ticker",
            "Security": "company_name",
            "GICS Sector": "sector",
        }
    )
    sp500["ticker"] = sp500["ticker"].str.replace(".", "-", regex=False)
    sp500 = sp500.sort_values("ticker").head(PILOT_SIZE).reset_index(drop=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Static firm universe: first 100 S&P 500 constituents by ticker (alphabetical).\n"
        f"# Source: Wikipedia List of S&P 500 companies ({SOURCE_URL}), snapshot Jan 2026.\n"
        "# GVKEY and PERMNO are intentionally absent; CIK is populated by SEC bootstrap.\n"
    )
    with OUTPUT.open("w", encoding="utf-8") as fh:
        fh.write(header)
        sp500[["ticker", "company_name", "sector"]].to_csv(fh, index=False)

    print(f"Wrote {len(sp500)} firms to {OUTPUT}")


if __name__ == "__main__":
    main()
