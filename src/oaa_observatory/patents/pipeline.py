"""AI patent pipeline for organizational investment signals."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.models import PatentsConfig
from oaa_observatory.ingestion.base import BasePipeline
from oaa_observatory.utils.logging import logger


class PatentsPipeline(BasePipeline):
    """Pipeline for AI-related patent counts by firm-year.

    Uses CPC classification prefixes to identify AI-related patents.
    Researchers define their own classification schemes downstream.
    """

    def __init__(self, config: PatentsConfig | None = None) -> None:
        """Initialize patents pipeline."""
        super().__init__(config or PatentsConfig())
        self._config: PatentsConfig = self.config  # type: ignore[assignment]

    def ingest(self) -> Path:
        """Ingest patent data from USPTO or WRDS Patent Intelligence."""
        self.raw_path.mkdir(parents=True, exist_ok=True)
        logger.info("Patents ingest: place raw patent extracts in {}", self.raw_path)
        return self.raw_path

    def standardize(self) -> Path:
        """Standardize patents to firm-patent records with CPC codes."""
        output = self.intermediate_path / "patents.parquet"
        self.intermediate_path.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(
            columns=[
                "patent_id",
                "firm_id",
                "filing_date",
                "grant_year",
                "cpc_codes",
                "is_ai_patent",
                "source",
            ]
        )
        return self.write_stage_output(df, output, stage="intermediate")

    def extract_features(self) -> Path:
        """Aggregate patent records to firm-year investment signals."""
        output = self.features_path / "firm_year.parquet"
        self.features_path.mkdir(parents=True, exist_ok=True)

        intermediate = self.intermediate_path / "patents.parquet"
        if not intermediate.exists():
            df = pd.DataFrame(
                columns=[
                    "firm_id",
                    "year",
                    "source",
                    "event_count",
                    "ai_patent_count",
                ]
            )
            return self.write_stage_output(df, output, stage="features")

        patents = pd.read_parquet(intermediate)
        if patents.empty:
            features = pd.DataFrame(
                columns=["firm_id", "year", "source", "event_count", "ai_patent_count"]
            )
        else:
            ai_patents = patents[patents["is_ai_patent"] == True]  # noqa: E712
            features = (
                ai_patents.groupby(["firm_id", "grant_year"], dropna=False)
                .size()
                .reset_index(name="ai_patent_count")
                .rename(columns={"grant_year": "year"})
            )
            features["event_count"] = features["ai_patent_count"]
            features["source"] = self._config.name

        return self.write_stage_output(features, output, stage="features")

    def classify_ai_patent(self, cpc_codes: list[str]) -> bool:
        """Determine if patent CPC codes match configured AI prefixes.

        Args:
            cpc_codes: List of CPC classification codes.

        Returns:
            True if any code matches an AI prefix.
        """
        for code in cpc_codes:
            for prefix in self._config.cpc_prefixes:
                if code.startswith(prefix):
                    return True
        return False
