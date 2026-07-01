"""Compute classifier validation metrics from human labels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def compute_validation_metrics(
    labels_path: Path,
    scores_path: Path | None = None,
) -> dict[str, float | int]:
    """Compute precision, recall, and F1 for keyword classifier vs human labels.

    Args:
        labels_path: Blind labeling CSV with ``sample_id`` and ``human_ai_mention``.
        scores_path: Model predictions CSV (``keyword_predicted``). Defaults to
            ``attention_scores.csv`` beside the labels file. Legacy combined CSVs
            that include both columns are still accepted when ``scores_path`` is
            omitted and ``keyword_predicted`` is present in ``labels_path``.

    Returns:
        Dictionary of metric name → value.

    Raises:
        ValueError: If no labeled rows exist or predictions cannot be joined.
    """
    labels = pd.read_csv(labels_path)
    if "human_ai_mention" not in labels.columns:
        msg = "Labels file missing human_ai_mention column"
        raise ValueError(msg)

    if scores_path is None and "keyword_predicted" in labels.columns:
        df = labels
    else:
        if scores_path is None:
            scores_path = labels_path.parent / "attention_scores.csv"
        if not scores_path.exists():
            msg = f"Scores file not found: {scores_path}"
            raise ValueError(msg)
        scores = pd.read_csv(scores_path)
        if "sample_id" not in labels.columns or "sample_id" not in scores.columns:
            msg = "Labels and scores files must both include sample_id"
            raise ValueError(msg)
        df = labels.merge(scores[["sample_id", "keyword_predicted"]], on="sample_id", how="inner")
        if df.empty:
            msg = "No rows matched between labels and scores on sample_id"
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
    scores_path: Path | None = None,
) -> Path:
    """Write validation metrics to a Markdown report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores_note = f"`{scores_path}`" if scores_path else "_combined labels file_"
    fp_rate = metrics["fp"] / (metrics["fp"] + metrics["tn"]) if (metrics["fp"] + metrics["tn"]) else 0.0
    fn_rate = metrics["fn"] / (metrics["fn"] + metrics["tp"]) if (metrics["fn"] + metrics["tp"]) else 0.0
    body = f"""# Attention Classifier Validation

Source labels: `{labels_path}`
Source scores: {scores_note}

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

## Error analysis

Review false positives and false negatives separately — they imply different fixes.

| Error type | Count | Share of relevant class | Likely cause |
|------------|------:|------------------------:|--------------|
| False positives (human=0, keyword=1) | {metrics['fp']} | {fp_rate:.1%} of human non-AI | Keyword list too loose — boilerplate risk factors, legal disclaimers, passing references |
| False negatives (human=1, keyword=0) | {metrics['fn']} | {fn_rate:.1%} of human AI | Missing vocabulary — synonyms, product names (Copilot, etc.), phrasing outside keyword list |

Low **precision** → tighten or contextualize keywords. Low **recall** → expand keywords or move to a supervised classifier.

## Interpretation

The keyword counter is a transparent baseline, not a validated classifier.
Use the error breakdown above before citing attention metrics in downstream work.
"""
    output_path.write_text(body, encoding="utf-8")
    return output_path


def render_pending_template(output_path: Path, labels_path: Path) -> Path:
    """Write a template report when human labels are not yet available."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# Attention Classifier Validation

Source labels: `{labels_path}`

## Labeling rule

_Write your one-sentence rule here before labeling begins, then apply it consistently._

> Example: Count as AI mention (1) only when the excerpt substantively discusses AI/ML
> strategy, products, investment, or operations — not generic risk-factor boilerplate
> that merely names "artificial intelligence" without firm-specific content.

## Status

**Pending human labeling.** Fill ``human_ai_mention`` (0 or 1) in the blind labeling CSV
``data/validation/attention_labeling.csv``. That file shows only ``sample_id`` and
``excerpt`` — do not open ``attention_scores.csv`` until labeling is complete.

Then run:

```bash
oaa validation run
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
