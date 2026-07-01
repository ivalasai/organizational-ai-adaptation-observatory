"""Tests for attention classifier validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from oaa_observatory.validation import (
    compute_validation_metrics,
    generate_validation_sample,
    render_pending_template,
    write_validation_report,
)


class TestValidation:
    def test_generate_sample(self, tmp_path: Path) -> None:
        docs = tmp_path / "documents.parquet"
        pd.DataFrame(
            [
                {
                    "document_id": f"d{i}",
                    "firm_id": "OAA-a",
                    "ticker": "TST",
                    "fiscal_year": 2020 + (i % 5),
                    "form_type": "10-K",
                    "text": "machine learning" if i % 2 == 0 else "ordinary business",
                }
                for i in range(50)
            ]
        ).to_parquet(docs)
        labeling = tmp_path / "labeling.csv"
        scores = tmp_path / "scores.csv"
        generate_validation_sample(docs, labeling, scores, sample_size=20)
        blind = pd.read_csv(labeling)
        scored = pd.read_csv(scores)
        assert len(blind) <= 20
        assert len(blind) == len(scored)
        assert list(blind.columns) == ["sample_id", "excerpt", "human_ai_mention"]
        assert "keyword_predicted" not in blind.columns
        assert "keyword_predicted" in scored.columns

    def test_metrics_with_labels(self, tmp_path: Path) -> None:
        labels = tmp_path / "labels.csv"
        scores = tmp_path / "scores.csv"
        pd.DataFrame(
            {
                "sample_id": ["a", "b", "c", "d"],
                "human_ai_mention": [1, 0, 0, 0],
            }
        ).to_csv(labels, index=False)
        pd.DataFrame(
            {
                "sample_id": ["a", "b", "c", "d"],
                "keyword_predicted": [1, 0, 1, 0],
            }
        ).to_csv(scores, index=False)
        metrics = compute_validation_metrics(labels, scores)
        assert metrics["precision"] == 0.5
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == pytest.approx(2 / 3)

    def test_metrics_legacy_combined_file(self, tmp_path: Path) -> None:
        labels = tmp_path / "labels.csv"
        pd.DataFrame(
            {
                "keyword_predicted": [1, 0, 1, 0],
                "human_ai_mention": [1, 0, 0, 0],
            }
        ).to_csv(labels, index=False)
        metrics = compute_validation_metrics(labels)
        assert metrics["precision"] == 0.5

    def test_pending_template(self, tmp_path: Path) -> None:
        report = tmp_path / "report.md"
        render_pending_template(report, tmp_path / "labels.csv")
        assert "Pending human labeling" in report.read_text()

    def test_write_report(self, tmp_path: Path) -> None:
        report = tmp_path / "report.md"
        metrics = {
            "n_labeled": 10,
            "tp": 5,
            "fp": 1,
            "fn": 2,
            "tn": 2,
            "precision": 0.8333,
            "recall": 0.7143,
            "f1": 0.7692,
        }
        write_validation_report(metrics, report, tmp_path / "labels.csv")
        text = report.read_text()
        assert "0.8333" in text
