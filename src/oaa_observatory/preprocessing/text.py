"""Text preprocessing utilities for document standardization."""

from __future__ import annotations

import re
import unicodedata


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text to NFKC form.

    Args:
        text: Raw input text.

    Returns:
        Normalized text string.
    """
    return unicodedata.normalize("NFKC", text)


def collapse_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters to single spaces.

    Args:
        text: Input text.

    Returns:
        Text with normalized whitespace.
    """
    return re.sub(r"\s+", " ", text).strip()


def preprocess_document(text: str) -> str:
    """Apply standard preprocessing pipeline to document text.

    Args:
        text: Raw document text.

    Returns:
        Preprocessed text ready for feature extraction.
    """
    text = normalize_unicode(text)
    return collapse_whitespace(text)
