"""Base classes and interfaces for data ingestion pipelines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from oaa_observatory.config.models import DataSourceConfig
from oaa_observatory.config.settings import Settings, get_settings
from oaa_observatory.schemas.records import PipelineStageMetadata
from oaa_observatory.utils.io import write_parquet_atomic
from oaa_observatory.utils.logging import logger


class BasePipeline(ABC):
    """Abstract base class for reproducible data pipelines.

    Each pipeline follows the staged data model:

        raw → intermediate → features → (panel assembly)
    """

    def __init__(
        self,
        config: DataSourceConfig,
        settings: Settings | None = None,
    ) -> None:
        """Initialize pipeline with datasource configuration.

        Args:
            config: Data source configuration.
            settings: Application settings. Uses defaults if not provided.
        """
        self.config = config
        self.settings = settings or get_settings()
        self.settings.ensure_directories()

    @property
    def raw_path(self) -> Path:
        """Directory for immutable raw data for this source."""
        return self.settings.raw_dir / self.config.raw_subdir

    @property
    def intermediate_path(self) -> Path:
        """Directory for standardized intermediate tables."""
        return self.settings.intermediate_dir / self.config.intermediate_subdir

    @property
    def features_path(self) -> Path:
        """Directory for firm-year feature outputs."""
        return self.settings.features_dir / self.config.features_subdir

    def _stage_metadata(self, stage: str, row_count: int) -> dict[str, Any]:
        return PipelineStageMetadata(
            stage=stage,  # type: ignore[arg-type]
            source=self.config.name,
            signal_layer=self.config.signal_layer,
            created_at=datetime.now(tz=UTC),
            row_count=row_count,
        ).model_dump()

    def write_stage_output(
        self,
        df: pd.DataFrame,
        path: Path,
        stage: str,
    ) -> Path:
        """Write pipeline stage output with metadata.

        Args:
            df: Output DataFrame.
            path: Destination path.
            stage: Pipeline stage name.

        Returns:
            Path to written file.
        """
        metadata = self._stage_metadata(stage=stage, row_count=len(df))
        logger.info(
            "Writing {} rows to {} (stage={}, source={})",
            len(df),
            path,
            stage,
            self.config.name,
        )
        return write_parquet_atomic(df, path, metadata=metadata)

    @abstractmethod
    def ingest(self) -> Path:
        """Ingest raw data from external source.

        Returns:
            Path to raw data directory or manifest.
        """

    @abstractmethod
    def standardize(self) -> Path:
        """Transform raw data into standardized intermediate tables.

        Returns:
            Path to intermediate output.
        """

    @abstractmethod
    def extract_features(self) -> Path:
        """Extract firm-year signals from intermediate data.

        Returns:
            Path to features output.
        """

    def run(self) -> Path:
        """Execute the full pipeline: ingest → standardize → features.

        Returns:
            Path to final features output.
        """
        logger.info("Starting pipeline for source={}", self.config.name)
        if self.config.enabled:
            self.ingest()
            self.standardize()
            return self.extract_features()
        logger.warning("Pipeline disabled for source={}", self.config.name)
        return self.features_path
