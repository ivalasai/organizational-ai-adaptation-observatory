"""Parse SEC filing documents to plain text."""

from __future__ import annotations

import re
import warnings
from html import unescape

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_LARGE_FILE_BYTES = 500_000


def html_to_text(content: str) -> str:
    """Convert HTML or HTML-like filing content to plain text."""
    soup = BeautifulSoup(content, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return collapse_whitespace(unescape(text))


def collapse_whitespace(text: str) -> str:
    """Collapse runs of whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def _fast_strip_tags(text: str) -> str:
    """Fast tag-stripping for large XBRL/HTML documents."""
    return collapse_whitespace(unescape(re.sub(r"<[^>]+>", " ", text)))


def parse_filing_bytes(content: bytes) -> str:
    """Parse raw filing bytes to plain text.

    Uses fast tag-stripping for large files; BeautifulSoup for smaller HTML.
    """
    if len(content) > _LARGE_FILE_BYTES:
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            decoded = content.decode("latin-1", errors="ignore")
        return _fast_strip_tags(decoded)

    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1", errors="ignore")

    lower = decoded.lower()
    if "<html" in lower or "<body" in lower or "<div" in lower:
        return html_to_text(decoded)

    return _fast_strip_tags(decoded)
