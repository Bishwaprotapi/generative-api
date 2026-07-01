"""
Redis client initialisation.
Returns a connected client or None when caching is disabled / unavailable.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def init_redis() -> None:
    """Create the shared Redis connection pool on app startup."""
    global _redis_client
    if not settings.ENABLE_CACHE:
        logger.info("Cache disabled — skipping Redis initialisation.")
        return
    try:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await _redis_client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable (%s) — cache will be disabled.", exc)
        _redis_client = None


async def close_redis() -> None:
    """Close the Redis connection pool on app shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def get_redis() -> aioredis.Redis | None:
    """Return the active Redis client or None."""
    return _redis_client
