"""Compute classifier validation metrics from human labels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def compute_validation_metrics(labels_path: Path) -> dict[str, float | int]:
    """Compute precision, recall, and F1 for keyword classifier vs human labels.

    Args:
        labels_path: CSV with ``keyword_predicted`` and filled ``human_ai_mention``.

    Returns:
        Dictionary of metric name → value.

    Raises:
        ValueError: If no labeled rows exist.
    """
    df = pd.read_csv(labels_path)
    if "human_ai_mention" not in df.columns:
        msg = "Labels file missing human_ai_mention column"
        raise ValueError(msg)

    labeled = df[df["human_ai_mention"].astype(str).str.strip().isin({"0", "1"})].copy()
    if labeled.empty:
        msg = "No human labels found — fill human_ai_mention column first"
        raise ValueError(msg)

    y_true = labeled["human_ai_mention"].astype(int)
    y_pred = labeled["keyword_predicted"].astype(int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "n_labeled": len(labeled),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def write_validation_report(
    metrics: dict[str, float | int],
    output_path: Path,
    labels_path: Path,
) -> Path:
    """Write validation metrics to a Markdown report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# Attention Classifier Validation

Source labels: `{labels_path}`

## Status

Metrics computed from **{metrics['n_labeled']}** human-labeled excerpts.

## Confusion matrix

| | Predicted AI | Predicted non-AI |
|---|---|---|
| **Human AI** | {metrics['tp']} | {metrics['fn']} |
| **Human non-AI** | {metrics['fp']} | {metrics['tn']} |

## Metrics

| Metric | Value |
|--------|------:|
| Precision | {metrics['precision']:.4f} |
| Recall | {metrics['recall']:.4f} |
| F1 | {metrics['f1']:.4f} |

## Interpretation

The keyword counter is a transparent baseline, not a validated classifier.
Review false positives and false negatives to refine the keyword list or
replace with a supervised model in downstream work.
"""
    output_path.write_text(body, encoding="utf-8")
    return output_path


def render_pending_template(output_path: Path, labels_path: Path) -> Path:
    """Write a template report when human labels are not yet available."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# Attention Classifier Validation

Source labels: `{labels_path}`

## Status

**Pending human labeling.** Fill the ``human_ai_mention`` column in the labels CSV
(1 = excerpt discusses AI/ML topics, 0 = does not), then run:

```bash
oaa validation run --labels {labels_path}
```

## Metrics

| Metric | Value |
|--------|------:|
| Precision | _pending_ |
| Recall | _pending_ |
| F1 | _pending_ |

Do not cite this layer as validated until real numbers appear above.
"""
    output_path.write_text(body, encoding="utf-8")
    return output_path
