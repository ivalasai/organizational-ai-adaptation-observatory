"""Keyword-based text counting for attention signal extraction.

This module provides simple, transparent term-matching utilities.
It deliberately avoids sentiment models, hype classifiers, or latent constructs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordCountResult:
    """Result of keyword counting on a text document."""

    mention_count: int
    total_tokens: int
    keyword_token_count: int
    matched_keywords: tuple[str, ...]


class KeywordCounter:
    """Count occurrences of configured keywords in text.

    Uses case-insensitive whole-word matching for reproducibility
    and interpretability. Researchers can substitute alternative
    NLP modules without changing pipeline interfaces.
    """

    def __init__(self, keywords: list[str]) -> None:
        """Initialize counter with a keyword list.

        Args:
            keywords: Terms to search for (case-insensitive).
        """
        self._keywords = tuple(kw.lower().strip() for kw in keywords if kw.strip())
        patterns = [rf"\b{re.escape(kw)}\b" for kw in self._keywords]
        self._pattern = re.compile("|".join(patterns), re.IGNORECASE) if patterns else None

    def count(self, text: str) -> KeywordCountResult:
        """Count keyword mentions in text.

        Args:
            text: Input document text.

        Returns:
            KeywordCountResult with mention and token statistics.
        """
        if not text or self._pattern is None:
            return KeywordCountResult(
                mention_count=0,
                total_tokens=0,
                keyword_token_count=0,
                matched_keywords=(),
            )

        tokens = text.split()
        total_tokens = len(tokens)
        matches = self._pattern.findall(text)
        mention_count = len(matches)

        matched_set: set[str] = set()
        for match in matches:
            matched_set.add(match.lower())

        return KeywordCountResult(
            mention_count=mention_count,
            total_tokens=total_tokens,
            keyword_token_count=len(matches),
            matched_keywords=tuple(sorted(matched_set)),
        )
