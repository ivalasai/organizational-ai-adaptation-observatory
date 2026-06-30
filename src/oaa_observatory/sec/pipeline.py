"""SEC EDGAR filings pipeline for organizational attention signals."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.models import SECConfig
from oaa_observatory.ingestion.base import BasePipeline
from oaa_observatory.nlp.keyword_counter import KeywordCounter
from oaa_observatory.utils.logging import logger


class SECFilingsPipeline(BasePipeline):
    """Pipeline for SEC filing AI attention signals.

    Extracts structured counts of AI-related term mentions from
    10-K, 10-Q, and 8-K filings. Does not compute sentiment or hype scores.
    """

    def __init__(self, config: SECConfig | None = None) -> None:
        """Initialize SEC filings pipeline."""
        super().__init__(config or SECConfig())
        self._config: SECConfig = self.config  # type: ignore[assignment]
        self._keyword_counter = KeywordCounter(self._config.ai_keywords)

    def ingest(self) -> Path:
        """Ingest SEC filings from EDGAR.

        Note:
            Full EDGAR download not implemented in v0.1.
            Expects pre-downloaded raw files or WRDS SEC extracts.
        """
        self.raw_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "SEC ingest: place raw filings in {} or configure WRDS extract",
            self.raw_path,
        )
        return self.raw_path

    def standardize(self) -> Path:
        """Standardize raw SEC filings into document-level records.

        Returns:
            Path to intermediate Parquet file.
        """
        output = self.intermediate_path / "documents.parquet"
        self.intermediate_path.mkdir(parents=True, exist_ok=True)

        # Placeholder: in production, reads from raw_path manifest
        columns = [
            "document_id",
            "firm_id",
            "cik",
            "filing_type",
            "filing_date",
            "fiscal_year",
            "text",
            "source",
        ]
        df = pd.DataFrame(columns=columns)
        return self.write_stage_output(df, output, stage="intermediate")

    def extract_features(self) -> Path:
        """Aggregate document-level AI mentions to firm-year attention signals.

        Returns:
            Path to firm-year features Parquet file.
        """
        intermediate = self.intermediate_path / "documents.parquet"
        output = self.features_path / "firm_year.parquet"
        self.features_path.mkdir(parents=True, exist_ok=True)

        if not intermediate.exists():
            logger.warning("No intermediate SEC data found; writing empty features table")
            columns = [
                "firm_id",
                "year",
                "source",
                "document_count",
                "ai_mention_count",
                "ai_mention_share",
                "total_tokens",
                "ai_token_count",
            ]
            df = pd.DataFrame(columns=columns)
            return self.write_stage_output(df, output, stage="features")

        documents = pd.read_parquet(intermediate)
        features = self._aggregate_attention(documents)
        return self.write_stage_output(features, output, stage="features")

    def _aggregate_attention(self, documents: pd.DataFrame) -> pd.DataFrame:
        """Aggregate document-level counts to firm-year attention metrics."""
        if documents.empty:
            return pd.DataFrame(
                columns=[
                    "firm_id",
                    "year",
                    "source",
                    "document_count",
                    "ai_mention_count",
                    "ai_mention_share",
                    "total_tokens",
                    "ai_token_count",
                ]
            )

        records: list[dict[str, object]] = []
        for _, row in documents.iterrows():
            text = str(row.get("text", ""))
            counts = self._keyword_counter.count(text)
            records.append(
                {
                    "document_id": row["document_id"],
                    "firm_id": row["firm_id"],
                    "year": row["fiscal_year"],
                    "ai_mention_count": counts.mention_count,
                    "total_tokens": counts.total_tokens,
                    "ai_token_count": counts.keyword_token_count,
                    "has_ai_mention": counts.mention_count > 0,
                }
            )

        doc_features = pd.DataFrame(records)
        aggregated = (
            doc_features.groupby(["firm_id", "year"], dropna=False)
            .agg(
                document_count=("document_id", "count"),
                ai_mention_count=("ai_mention_count", "sum"),
                total_tokens=("total_tokens", "sum"),
                ai_token_count=("ai_token_count", "sum"),
                ai_document_count=("has_ai_mention", "sum"),
            )
            .reset_index()
        )
        aggregated["ai_mention_share"] = aggregated["ai_document_count"] / aggregated[
            "document_count"
        ].clip(lower=1)
        aggregated["source"] = self._config.name
        return aggregated.drop(columns=["ai_document_count"])
