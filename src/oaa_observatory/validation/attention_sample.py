"""Generate stratified validation sample for attention keyword classifier."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from oaa_observatory.nlp.keyword_counter import KeywordCounter

DEFAULT_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network",
    "generative ai",
    "large language model",
    "natural language processing",
    "computer vision",
]

EXCERPT_CHARS = 500
SAMPLE_SIZE = 250


def _excerpt(text: str, length: int = EXCERPT_CHARS) -> str:
    text = text.strip()
    if len(text) <= length:
        return text
    return text[:length] + "..."


def generate_validation_sample(
    documents_path: Path,
    labeling_path: Path,
    scores_path: Path | None = None,
    sample_size: int = SAMPLE_SIZE,
    keywords: list[str] | None = None,
) -> tuple[Path, Path]:
    """Sample filing excerpts stratified by year and AI-mention density.

    Writes two CSVs so human labeling stays blind to model output:

    * **Labeling file** — ``sample_id``, ``excerpt``, blank ``human_ai_mention``
    * **Scores file** — metadata + ``keyword_predicted`` / ``ai_mention_count``
      (used only when running ``oaa validation run``)

    Args:
        documents_path: Intermediate documents Parquet from SEC pipeline.
        labeling_path: Blind labeling CSV for manual work.
        scores_path: Model-side CSV (defaults to ``labeling_path`` sibling
            ``attention_scores.csv``).
        sample_size: Target number of excerpts (approximate after stratification).
        keywords: Keyword list for classifier predictions in the scores file.

    Returns:
        ``(labeling_path, scores_path)`` tuple.
    """
    if scores_path is None:
        scores_path = labeling_path.parent / "attention_scores.csv"
    counter = KeywordCounter(keywords or DEFAULT_KEYWORDS)
    docs = pd.read_parquet(documents_path)
    if docs.empty:
        msg = "No documents available for validation sampling"
        raise ValueError(msg)

    records: list[dict[str, object]] = []
    for _, row in docs.iterrows():
        text = str(row.get("text", ""))
        counts = counter.count(text)
        records.append(
            {
                "document_id": row["document_id"],
                "firm_id": row["firm_id"],
                "ticker": row.get("ticker", ""),
                "fiscal_year": int(row["fiscal_year"]),
                "form_type": row.get("form_type", ""),
                "ai_mention_count": counts.mention_count,
                "density_bin": _density_bin(counts.mention_count),
                "excerpt": _excerpt(text),
                "keyword_predicted": int(counts.mention_count > 0),
            }
        )

    pool = pd.DataFrame(records)
    per_bin = max(1, sample_size // pool["density_bin"].nunique())
    sampled_parts: list[pd.DataFrame] = []
    for (_, _), group in pool.groupby(["fiscal_year", "density_bin"], group_keys=False):
        sampled_parts.append(group.sample(n=min(len(group), per_bin), random_state=42))
    sampled = pd.concat(sampled_parts, ignore_index=True)
    # Avoid truncation bias: `groupby(..., sort=True)` + `.head(sample_size)` would
    # over-select earlier years. Downsample uniformly across the stratified set.
    if len(sampled) > sample_size:
        sampled = sampled.sample(n=sample_size, random_state=42).reset_index(
            drop=True
        )
    sampled["sample_id"] = sampled["document_id"].apply(
        lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:12]
    )

    labeling_path.parent.mkdir(parents=True, exist_ok=True)
    sampled[["sample_id", "excerpt"]].assign(human_ai_mention="").to_csv(
        labeling_path, index=False
    )
    scored_cols = [
        "sample_id",
        "document_id",
        "firm_id",
        "ticker",
        "fiscal_year",
        "form_type",
        "ai_mention_count",
        "density_bin",
        "keyword_predicted",
    ]
    sampled[scored_cols].to_csv(scores_path, index=False)
    return labeling_path, scores_path


def _density_bin(mention_count: int) -> str:
    if mention_count == 0:
        return "zero"
    if mention_count <= 5:
        return "low"
    if mention_count <= 20:
        return "medium"
    return "high"
