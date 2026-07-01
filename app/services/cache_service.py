"""
Cache service.

Wraps Redis with a clean async interface. Cache is keyed by a hash
that includes: provider, model, prompt hash, and extra params.
Falls back silently when Redis is unavailable or caching is disabled.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.cache import get_redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _make_key(provider: str, model: str, prompt: str, extra: dict[str, Any] | None = None) -> str:
    """Build a deterministic cache key from request parameters."""
    raw = json.dumps(
        {"provider": provider, "model": model, "prompt": prompt, "extra": extra or {}},
        sort_keys=True,
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"llm:cache:{digest}"


class CacheService:
    """High-level cache operations backed by Redis."""

    async def get(self, key: str) -> str | None:
        """Return cached value or None."""
        redis = get_redis()
        if redis is None or not settings.ENABLE_CACHE:
            return None
        try:
            return await redis.get(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache GET failed: %s", exc)
            return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store value with optional TTL (defaults to CACHE_TTL from settings)."""
        redis = get_redis()
        if redis is None or not settings.ENABLE_CACHE:
            return
        try:
            await redis.set(key, value, ex=ttl or settings.CACHE_TTL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache SET failed: %s", exc)

    async def delete(self, key: str) -> None:
        """Evict a cache entry."""
        redis = get_redis()
        if redis is None:
            return
        try:
            await redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache DELETE failed: %s", exc)

    async def get_llm(
        self,
        provider: str,
        model: str,
        prompt: str,
        extra: dict[str, Any] | None = None,
    ) -> str | None:
        """Convenience: get cached LLM response."""
        key = _make_key(provider, model, prompt, extra)
        return await self.get(key)

    async def set_llm(
        self,
        provider: str,
        model: str,
        prompt: str,
        value: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Convenience: cache an LLM response."""
        key = _make_key(provider, model, prompt, extra)
        await self.set(key, value)


cache_service = CacheService()
