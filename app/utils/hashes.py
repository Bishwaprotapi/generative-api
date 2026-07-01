"""
Hashing utilities (non-security use cases).
"""

from __future__ import annotations

import hashlib
import hmac


def sha256_hex(data: str | bytes) -> str:
    """Return the SHA-256 hex digest of *data*."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def md5_hex(data: str | bytes) -> str:
    """Return the MD5 hex digest of *data* (for checksums, not security)."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.md5(data).hexdigest()  # noqa: S324


def constant_time_compare(val1: str, val2: str) -> bool:
    """Timing-safe string comparison."""
    return hmac.compare_digest(val1.encode(), val2.encode())
