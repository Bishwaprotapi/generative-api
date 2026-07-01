"""
General-purpose utility helpers.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def paginate(items: list[Any], page: int, size: int) -> tuple[list[Any], int, int]:
    """
    Slice *items* for pagination.
    Returns (page_items, total, total_pages).
    """
    total = len(items)
    total_pages = max(1, math.ceil(total / size))
    start = (page - 1) * size
    return items[start : start + size], total, total_pages


def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    """Truncate *text* to *max_len* characters, appending *suffix* if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def flatten(nested: list[list[Any]]) -> list[Any]:
    """Flatten one level of nesting."""
    return [item for sublist in nested for item in sublist]
