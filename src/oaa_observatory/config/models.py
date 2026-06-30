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
    start_year: int = 2010
    end_year: int | None = None
    file_format: Literal["parquet", "csv", "json"] = "parquet"


class SECConfig(DataSourceConfig):
    """Configuration for SEC EDGAR filings ingestion."""

    name: str = "sec_filings"
    signal_layer: Literal["attention"] = "attention"
    raw_subdir: str = "sec"
    intermediate_subdir: str = "sec"
    features_subdir: str = "attention/sec"
    filing_types: list[str] = Field(default_factory=lambda: ["10-K", "10-Q", "8-K"])
    ai_keywords: list[str] = Field(
        default_factory=lambda: [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural network",
            "generative ai",
            "large language model",
        ]
    )


class EarningsCallsConfig(DataSourceConfig):
    """Configuration for earnings call transcript ingestion."""

    name: str = "earnings_calls"
    signal_layer: Literal["attention"] = "attention"
    raw_subdir: str = "earnings_calls"
    intermediate_subdir: str = "earnings_calls"
    features_subdir: str = "attention/earnings_calls"


class PatentsConfig(DataSourceConfig):
    """Configuration for AI patent signal extraction."""

    name: str = "patents"
    signal_layer: Literal["investment"] = "investment"
    raw_subdir: str = "patents"
    intermediate_subdir: str = "patents"
    features_subdir: str = "investment/patents"
    cpc_prefixes: list[str] = Field(default_factory=lambda: ["G06N", "G06F18"])


class JobsConfig(DataSourceConfig):
    """Configuration for AI job posting signal extraction."""

    name: str = "jobs"
    signal_layer: Literal["investment"] = "investment"
    raw_subdir: str = "jobs"
    intermediate_subdir: str = "jobs"
    features_subdir: str = "investment/jobs"
    ai_role_keywords: list[str] = Field(
        default_factory=lambda: [
            "machine learning engineer",
            "ai researcher",
            "data scientist",
            "mlops",
        ]
    )


class ProductsConfig(DataSourceConfig):
    """Configuration for public product and deployment evidence."""

    name: str = "products"
    signal_layer: Literal["deployment"] = "deployment"
    raw_subdir: str = "products"
    intermediate_subdir: str = "products"
    features_subdir: str = "deployment/products"
    event_types: list[str] = Field(
        default_factory=lambda: [
            "product_launch",
            "api_launch",
            "feature_release",
            "developer_documentation",
        ]
    )


class PanelBuilderConfig(BaseModel):
    """Configuration for assembling the firm-year panel."""

    output_path: Path = Path("data/panel/firm_year_panel.parquet")
    export_formats: list[Literal["parquet", "csv", "duckdb"]] = Field(
        default=["parquet", "csv"],
    )
    feature_tables: list[str] = Field(
        default_factory=lambda: [
            "attention/sec",
            "attention/earnings_calls",
            "investment/patents",
            "investment/jobs",
            "deployment/products",
        ]
    )
    join_keys: list[str] = Field(default_factory=lambda: ["firm_id", "year"])
    min_year: int = 2010
    max_year: int | None = None
