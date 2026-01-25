"""
Utilities for ensuring book cover URLs are present.
"""
from __future__ import annotations

from typing import Dict, List


try:
    from django.templatetags.static import static
    PLACEHOLDER_COVER_URL = static("images/placeholder.svg")
except Exception:
    PLACEHOLDER_COVER_URL = "https://example.com/placeholder_cover.png"


def normalize_cover(url) -> str:
    """
    Normalize a cover URL, returning a placeholder if the value is invalid.
    """
    if not isinstance(url, str):
        return PLACEHOLDER_COVER_URL
    candidate = url.strip()
    if not candidate or candidate.lower() in {"null", "none"}:
        return PLACEHOLDER_COVER_URL
    return candidate


def fill_missing_covers(books_list: List[Dict]) -> List[Dict]:
    """
    Ensure each book has a non-empty cover_url field.

    Existing cover_url values are preserved. Missing or blank values are
    filled with PLACEHOLDER_COVER_URL. The original order is preserved.
    """
    if not books_list:
        return books_list

    for book in books_list:
        if not isinstance(book, dict):
            continue
        book["cover_url"] = normalize_cover(book.get("cover_url"))

    return books_list
