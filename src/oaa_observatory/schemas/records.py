"""Canonical data schemas for pipeline stages."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class FirmIdentifier(BaseModel):
    """Canonical firm identifier with cross-reference aliases."""

    firm_id: str = Field(description="Canonical observatory firm identifier")
    gvkey: str | None = None
    cik: str | None = None
    ticker: str | None = None
    cusip: str | None = None
    permno: int | None = None
    company_name: str | None = None
    source: str = Field(description="Provenance of the identifier mapping")


class FirmYearRecord(BaseModel):
    """Base schema for firm-year panel records."""

    firm_id: str
    year: int
    gvkey: str | None = None
    cik: str | None = None
    ticker: str | None = None


class AttentionSignal(BaseModel):
    """Firm-year organizational attention signal record."""

    firm_id: str
    year: int
    source: str
    document_count: int = 0
    ai_mention_count: int = 0
    ai_mention_share: float | None = Field(
        default=None,
        description="Share of documents mentioning AI-related terms (not sentiment)",
    )
    total_tokens: int | None = None
    ai_token_count: int | None = None


class InvestmentSignal(BaseModel):
    """Firm-year organizational investment signal record."""

    firm_id: str
    year: int
    source: str
    event_count: int = 0
    ai_patent_count: int | None = None
    ai_job_posting_count: int | None = None
    ai_hiring_intensity: float | None = Field(
        default=None,
        description="Raw count or ratio; researchers define scaling",
    )


class DeploymentSignal(BaseModel):
    """Firm-year organizational deployment signal record."""

    firm_id: str
    year: int
    source: str
    product_launch_count: int = 0
    api_launch_count: int = 0
    feature_release_count: int = 0
    documentation_update_count: int = 0
    total_deployment_events: int = 0


class RawDocumentRecord(BaseModel):
    """Standardized raw document metadata before feature extraction."""

    document_id: str
    firm_id: str | None = None
    source: str
    document_type: str
    filing_date: date | None = None
    fiscal_year: int | None = None
    raw_path: str
    ingested_at: datetime


class PipelineStageMetadata(BaseModel):
    """Metadata attached to pipeline stage outputs."""

    stage: Literal["raw", "intermediate", "features", "panel", "exports"]
    source: str
    signal_layer: Literal["attention", "investment", "deployment"]
    created_at: datetime
    row_count: int
    config_hash: str | None = None
