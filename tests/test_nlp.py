"""Tests for NLP keyword counter."""

from oaa_observatory.nlp import KeywordCounter


class TestKeywordCounter:
    """Keyword counter test cases."""

    def test_count_mentions(self) -> None:
        counter = KeywordCounter(["machine learning", "artificial intelligence"])
        result = counter.count(
            "We use machine learning and artificial intelligence in our products."
        )
        assert result.mention_count == 2
        assert result.total_tokens == 10

    def test_case_insensitive(self) -> None:
        counter = KeywordCounter(["machine learning"])
        result = counter.count("Machine Learning is important.")
        assert result.mention_count == 1

    def test_empty_text(self) -> None:
        counter = KeywordCounter(["ai"])
        result = counter.count("")
        assert result.mention_count == 0
        assert result.total_tokens == 0

    def test_no_keywords_configured(self) -> None:
        counter = KeywordCounter([])
        result = counter.count("some text here")
        assert result.mention_count == 0
