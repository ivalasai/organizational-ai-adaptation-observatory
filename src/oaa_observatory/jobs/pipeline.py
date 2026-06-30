"""AI job posting pipeline for organizational investment signals."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.models import JobsConfig
from oaa_observatory.ingestion.base import BasePipeline
from oaa_observatory.utils.logging import logger


class JobsPipeline(BasePipeline):
    """Pipeline for AI-related job posting signals by firm-year.

    Counts postings matching configured role keywords.
    Does not infer hiring quality, seniority weights, or skill depth.
    """

    def __init__(self, config: JobsConfig | None = None) -> None:
        """Initialize jobs pipeline."""
        super().__init__(config or JobsConfig())
        self._config: JobsConfig = self.config  # type: ignore[assignment]

    def ingest(self) -> Path:
        """Ingest job posting data from public or licensed sources."""
        self.raw_path.mkdir(parents=True, exist_ok=True)
        logger.info("Jobs ingest: place raw job posting extracts in {}", self.raw_path)
        return self.raw_path

    def standardize(self) -> Path:
        """Standardize job postings to firm-posting records."""
        output = self.intermediate_path / "postings.parquet"
        self.intermediate_path.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(
            columns=[
                "posting_id",
                "firm_id",
                "post_date",
                "title",
                "is_ai_role",
                "source",
            ]
        )
        return self.write_stage_output(df, output, stage="intermediate")

    def extract_features(self) -> Path:
        """Aggregate job postings to firm-year investment signals."""
        output = self.features_path / "firm_year.parquet"
        self.features_path.mkdir(parents=True, exist_ok=True)

        intermediate = self.intermediate_path / "postings.parquet"
        if not intermediate.exists():
            df = pd.DataFrame(
                columns=[
                    "firm_id",
                    "year",
                    "source",
                    "event_count",
                    "ai_job_posting_count",
                    "ai_hiring_intensity",
                ]
            )
            return self.write_stage_output(df, output, stage="features")

        postings = pd.read_parquet(intermediate)
        if postings.empty:
            features = pd.DataFrame(
                columns=[
                    "firm_id",
                    "year",
                    "source",
                    "event_count",
                    "ai_job_posting_count",
                    "ai_hiring_intensity",
                ]
            )
        else:
            postings = postings.copy()
            postings["year"] = pd.to_datetime(postings["post_date"]).dt.year
            ai_postings = postings[postings["is_ai_role"] == True]  # noqa: E712
            features = (
                ai_postings.groupby(["firm_id", "year"], dropna=False)
                .size()
                .reset_index(name="ai_job_posting_count")
            )
            features["event_count"] = features["ai_job_posting_count"]
            features["ai_hiring_intensity"] = features["ai_job_posting_count"]
            features["source"] = self._config.name

        return self.write_stage_output(features, output, stage="features")

    def is_ai_role(self, title: str) -> bool:
        """Check if a job title matches configured AI role keywords.

        Args:
            title: Job posting title.

        Returns:
            True if title contains an AI role keyword.
        """
        title_lower = title.lower()
        return any(kw in title_lower for kw in self._config.ai_role_keywords)
