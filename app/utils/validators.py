"""
Input validators used across the application.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(
    r"^(https?://)"
    r"([a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+)$"
)


def is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value))


def is_valid_url(value: str) -> bool:
    return bool(_URL_RE.match(value))


def sanitize_filename(name: str) -> str:
    """Strip path separators and dangerous characters from a filename."""
    return re.sub(r"[^\w.\-]", "_", name.replace("/", "_").replace("\\", "_"))


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp *value* between *min_val* and *max_val*."""
    return max(min_val, min(max_val, value))
