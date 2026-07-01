"""Pydantic models for datasource and pipeline configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    """Base configuration shared by all data sources."""

    name: str
    enabled: bool = True
    signal_layer: Literal["attention", "investment", "deployment"]
    raw_subdir: str
    intermediate_subdir: str
    features_subdir: str
    start_year: int = 2015
    end_year: int | None = 2026
    file_format: Literal["parquet", "csv", "json"] = "parquet"


class SECConfig(DataSourceConfig):
    """Configuration for SEC EDGAR filings ingestion."""

    name: str = "sec_filings"
    signal_layer: Literal["attention"] = "attention"
    raw_subdir: str = "sec"
    intermediate_subdir: str = "sec"
    features_subdir: str = "attention/sec"
    start_year: int = 2015
    end_year: int = 2026
    filing_types: list[str] = Field(default_factory=lambda: ["10-K", "10-Q"])
    universe_path: Path = Path("data/universe/firm_universe.csv")
    ai_keywords: list[str] = Field(
        default_factory=lambda: [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural network",
            "generative ai",
            "large language model",
            "natural language processing",
            "computer vision",
        ]
    )


class PanelBuilderConfig(BaseModel):
    """Configuration for assembling the firm-year panel."""

    output_path: Path = Path("data/panel/firm_year_panel.parquet")
    export_formats: list[Literal["parquet", "csv", "duckdb"]] = Field(
        default=["parquet"],
    )
    feature_tables: list[str] = Field(
        default_factory=lambda: ["attention/sec"],
    )
    join_keys: list[str] = Field(default_factory=lambda: ["firm_id", "year"])
    min_year: int = 2015
    max_year: int | None = 2026
