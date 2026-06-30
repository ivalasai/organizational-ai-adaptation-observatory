"""Earnings call transcript pipeline for organizational attention signals."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.models import EarningsCallsConfig
from oaa_observatory.ingestion.base import BasePipeline
from oaa_observatory.utils.logging import logger


class EarningsCallsPipeline(BasePipeline):
    """Pipeline for earnings call transcript attention signals.

    Processes call-level transcripts into firm-year AI mention counts.
    Full transcript download requires licensed data (e.g., Refinitiv, FactSet).
    """

    def __init__(self, config: EarningsCallsConfig | None = None) -> None:
        """Initialize earnings calls pipeline."""
        super().__init__(config or EarningsCallsConfig())

    def ingest(self) -> Path:
        """Ingest earnings call transcripts."""
        self.raw_path.mkdir(parents=True, exist_ok=True)
        logger.info("Earnings calls ingest: place raw transcripts in {}", self.raw_path)
        return self.raw_path

    def standardize(self) -> Path:
        """Standardize transcripts to document-level records."""
        output = self.intermediate_path / "transcripts.parquet"
        self.intermediate_path.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(
            columns=[
                "document_id",
                "firm_id",
                "call_date",
                "fiscal_year",
                "quarter",
                "text",
                "source",
            ]
        )
        return self.write_stage_output(df, output, stage="intermediate")

    def extract_features(self) -> Path:
        """Extract firm-year attention features from call transcripts."""
        output = self.features_path / "firm_year.parquet"
        self.features_path.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(
            columns=[
                "firm_id",
                "year",
                "source",
                "call_count",
                "ai_mention_count",
                "ai_mention_share",
            ]
        )
        return self.write_stage_output(df, output, stage="features")
