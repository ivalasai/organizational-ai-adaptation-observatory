"""Tests for SEC EDGAR pipeline (mocked HTTP)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from oaa_observatory.config.models import SECConfig
from oaa_observatory.config.settings import Settings
from oaa_observatory.entity_resolution import EntityResolver
from oaa_observatory.sec.bootstrap import bootstrap_entity_resolution, load_firm_universe
from oaa_observatory.sec.client import SECClient
from oaa_observatory.sec.pipeline import SECFilingsPipeline


@pytest.fixture
def universe_csv(tmp_path: Path) -> Path:
    path = tmp_path / "universe.csv"
    path.write_text(
        "# test universe\n"
        "ticker,company_name,sector\n"
        "AAPL,Apple Inc.,Information Technology\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def ticker_json() -> dict[str, dict[str, str]]:
    return {
        "AAPL": {"cik": "0000320193", "title": "Apple Inc."},
        "MSFT": {"cik": "0000789019", "title": "Microsoft Corp"},
    }


class TestFirmUniverse:
    def test_load_skips_comments(self, universe_csv: Path) -> None:
        df = load_firm_universe(universe_csv)
        assert len(df) == 1
        assert "AAPL" in df["ticker"].values


class TestSECBootstrap:
    def test_bootstrap_maps_tickers(
        self,
        universe_csv: Path,
        tmp_path: Path,
        ticker_json: dict[str, dict[str, str]],
    ) -> None:
        mapping_path = tmp_path / "mappings.parquet"
        EntityResolver().save(mapping_path)
        mock_client = MagicMock()
        mock_client.fetch_company_tickers.return_value = ticker_json
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("oaa_observatory.sec.bootstrap.SECClient", return_value=mock_client):
            resolver = bootstrap_entity_resolution(
                universe_path=universe_csv,
                mapping_path=mapping_path,
                user_agent="test agent",
            )
        assert len(resolver.mapping_table) == 1
        assert mapping_path.exists()
        assert resolver.resolve("ticker", "AAPL") is not None


class TestSECPipeline:
    def test_extract_features_from_documents(self, tmp_path: Path) -> None:
        settings = Settings(data_root=tmp_path / "data")
        config = SECConfig(start_year=2020, end_year=2024)
        pipeline = SECFilingsPipeline(config=config, settings=settings)

        intermediate = pipeline.intermediate_path / "documents.parquet"
        intermediate.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {
                    "document_id": "d1",
                    "firm_id": "OAA-abc",
                    "cik": "0000320193",
                    "ticker": "AAPL",
                    "form_type": "10-K",
                    "filing_date": "2023-10-01",
                    "fiscal_year": 2023,
                    "text": "We invest in machine learning and artificial intelligence.",
                    "raw_path": "/tmp/x",
                },
                {
                    "document_id": "d2",
                    "firm_id": "OAA-abc",
                    "cik": "0000320193",
                    "ticker": "AAPL",
                    "form_type": "10-Q",
                    "filing_date": "2024-01-01",
                    "fiscal_year": 2024,
                    "text": "Revenue increased year over year.",
                    "raw_path": "/tmp/y",
                },
            ]
        ).to_parquet(intermediate)

        output = pipeline.extract_features()
        features = pd.read_parquet(output)
        assert len(features) == 2
        assert features["ai_mention_count"].sum() >= 1
        assert "ai_mention_share" in features.columns

    def test_ingest_skips_existing_downloads(
        self,
        universe_csv: Path,
        tmp_path: Path,
        ticker_json: dict[str, dict[str, str]],
    ) -> None:
        settings = Settings(data_root=tmp_path / "data")
        config = SECConfig(start_year=2023, end_year=2023, filing_types=["10-K"])
        pipeline = SECFilingsPipeline(
            config=config,
            settings=settings,
            universe_path=universe_csv,
        )
        mapping_path = tmp_path / "data" / "intermediate" / "entity_resolution" / "mappings.parquet"
        resolver = EntityResolver()
        from oaa_observatory.schemas.records import FirmIdentifier

        resolver.register(
            FirmIdentifier(
                firm_id="",
                cik="0000320193",
                ticker="AAPL",
                source="test",
            )
        )
        resolver.save(mapping_path)

        raw_file = pipeline._filing_path(
            "0000320193", "0000320193-23-000001", "aapl-20230930.htm"
        )
        raw_file.parent.mkdir(parents=True)
        raw_file.write_text("<html><body>machine learning</body></html>", encoding="utf-8")

        mock_client = MagicMock()
        mock_client.fetch_company_tickers.return_value = ticker_json
        mock_client.iter_all_filings.return_value = [
            {
                "accessionNumber": "0000320193-23-000001",
                "form": "10-K",
                "filingDate": "2023-11-03",
                "primaryDocument": "aapl-20230930.htm",
            }
        ]
        mock_client.download_filing.side_effect = AssertionError("should not download")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(pipeline, "bootstrap_identifiers") as mock_bootstrap,
            patch("oaa_observatory.sec.pipeline.SECClient", return_value=mock_client),
        ):
            mock_bootstrap.return_value = EntityResolver.load(mapping_path)
            pipeline._manifest_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                [
                    {
                        "firm_id": "OAA-x",
                        "ticker": "AAPL",
                        "cik": "0000320193",
                        "accession_number": "0000320193-23-000001",
                        "form_type": "10-K",
                        "filing_date": "2023-11-03",
                        "fiscal_year": 2023,
                        "primary_document": "aapl-20230930.htm",
                        "raw_path": str(raw_file),
                    }
                ]
            ).to_parquet(pipeline._manifest_path)
            pipeline.ingest()
        mock_client.download_filing.assert_not_called()


class TestSECClient:
    def test_parse_filing_batch(self) -> None:
        batch = {
            "accessionNumber": ["0001", "0002"],
            "form": ["10-K", "10-Q"],
        }
        rows = SECClient._parse_filing_batch(batch)
        assert len(rows) == 2
        assert rows[0]["form"] == "10-K"
