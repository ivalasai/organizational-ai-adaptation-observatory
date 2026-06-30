"""Public product evidence pipeline for organizational deployment signals."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.models import ProductsConfig
from oaa_observatory.ingestion.base import BasePipeline
from oaa_observatory.utils.logging import logger


class ProductsPipeline(BasePipeline):
    """Pipeline for public product and deployment evidence by firm-year.

    Tracks product launches, API releases, feature updates, and
    developer documentation as observable deployment events.
    """

    def __init__(self, config: ProductsConfig | None = None) -> None:
        """Initialize products pipeline."""
        super().__init__(config or ProductsConfig())
        self._config: ProductsConfig = self.config  # type: ignore[assignment]

    def ingest(self) -> Path:
        """Ingest public product evidence from configured sources."""
        self.raw_path.mkdir(parents=True, exist_ok=True)
        logger.info("Products ingest: place raw product evidence in {}", self.raw_path)
        return self.raw_path

    def standardize(self) -> Path:
        """Standardize deployment events to structured records."""
        output = self.intermediate_path / "events.parquet"
        self.intermediate_path.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(
            columns=[
                "event_id",
                "firm_id",
                "event_date",
                "event_type",
                "description",
                "source_url",
                "source",
            ]
        )
        return self.write_stage_output(df, output, stage="intermediate")

    def extract_features(self) -> Path:
        """Aggregate deployment events to firm-year signals."""
        output = self.features_path / "firm_year.parquet"
        self.features_path.mkdir(parents=True, exist_ok=True)

        intermediate = self.intermediate_path / "events.parquet"
        if not intermediate.exists():
            df = pd.DataFrame(
                columns=[
                    "firm_id",
                    "year",
                    "source",
                    "product_launch_count",
                    "api_launch_count",
                    "feature_release_count",
                    "documentation_update_count",
                    "total_deployment_events",
                ]
            )
            return self.write_stage_output(df, output, stage="features")

        events = pd.read_parquet(intermediate)
        if events.empty:
            features = pd.DataFrame(
                columns=[
                    "firm_id",
                    "year",
                    "source",
                    "product_launch_count",
                    "api_launch_count",
                    "feature_release_count",
                    "documentation_update_count",
                    "total_deployment_events",
                ]
            )
        else:
            events = events.copy()
            events["year"] = pd.to_datetime(events["event_date"]).dt.year
            pivot = (
                events.groupby(["firm_id", "year", "event_type"], dropna=False)
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
            for col, event_type in [
                ("product_launch_count", "product_launch"),
                ("api_launch_count", "api_launch"),
                ("feature_release_count", "feature_release"),
                ("documentation_update_count", "developer_documentation"),
            ]:
                pivot[col] = pivot[event_type] if event_type in pivot.columns else 0

            count_cols = [
                "product_launch_count",
                "api_launch_count",
                "feature_release_count",
                "documentation_update_count",
            ]
            pivot["total_deployment_events"] = pivot[count_cols].sum(axis=1)
            pivot["source"] = self._config.name
            features = pivot[["firm_id", "year", "source", *count_cols, "total_deployment_events"]]

        return self.write_stage_output(features, output, stage="features")
