"""Tests for manual Compustat CSV import."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from oaa_observatory.financial_controls import load_compustat_export, merge_compustat_into_panel


@pytest.fixture
def compustat_csv(tmp_path: Path) -> Path:
    path = tmp_path / "compustat.csv"
    pd.DataFrame(
        [
            {
                "gvkey": "001690",
                "cik": 320193,
                "fyear": 2023,
                "at": 1000.0,
                "roa": 0.12,
                "sic": 3571,
                "emp": 50000,
            }
        ]
    ).to_csv(path, index=False)
    return path


class TestCompustatImport:
    def test_load_valid_export(self, compustat_csv: Path) -> None:
        df = load_compustat_export(compustat_csv)
        assert "year" in df.columns
        assert df.iloc[0]["cik"] == "0000320193"

    def test_missing_columns(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.csv"
        pd.DataFrame({"gvkey": ["1"]}).to_csv(path, index=False)
        with pytest.raises(ValueError, match="missing required columns"):
            load_compustat_export(path)

    def test_merge_into_panel(self, compustat_csv: Path) -> None:
        comp = load_compustat_export(compustat_csv)
        panel = pd.DataFrame(
            [{"firm_id": "OAA-a", "year": 2023, "ai_mention_count": 5}]
        )
        mapping = pd.DataFrame(
            [{"firm_id": "OAA-a", "cik": "0000320193", "ticker": "AAPL"}]
        )
        merged = merge_compustat_into_panel(panel, comp, mapping)
        assert "compustat_roa" in merged.columns
        assert merged.iloc[0]["compustat_roa"] == pytest.approx(0.12)
