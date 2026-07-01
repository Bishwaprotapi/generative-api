"""
Optional response-caching middleware.

When ENABLE_CACHE is True and a Redis client is available, GET responses
are stored in Redis. Subsequent identical requests are served from cache,
bypassing the route handler entirely.

Only safe (GET, HEAD) methods are cached.
Routes can opt out by returning a Cache-Control: no-store header.

Important: Swagger UI routes (/docs, /openapi.json, /redoc) must never be cached,
or the UI can break due to incorrect content-type/body handling.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.cache import get_redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHEABLE_METHODS = {"GET", "HEAD"}

# Never cache FastAPI docs / schema endpoints
_CACHE_EXCLUDE_PREFIXES = ("/docs", "/openapi.json", "/redoc")


class CacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        redis = get_redis()

        # Only attempt caching when Redis is live and cache is enabled
        if (
            not settings.ENABLE_CACHE
            or redis is None
            or request.method not in _CACHEABLE_METHODS
            or request.url.path.startswith(_CACHE_EXCLUDE_PREFIXES)
        ):
            return await call_next(request)

        cache_key = f"http:cache:{request.method}:{request.url}"

        try:
            cached = await redis.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: %s", request.url)
                # We only cache textual/JSON responses as plain text in Redis.
                # Return bytes directly; do NOT wrap in JSONResponse.
                return Response(
                    content=cached,
                    status_code=200,
                    headers={"X-Cache": "HIT"},
                    media_type="application/json",
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache middleware GET error: %s", exc)

        response = await call_next(request)

        # Do not cache non-200 responses or responses with no-store directive
        cache_control = response.headers.get("Cache-Control", "")
        if response.status_code == 200 and "no-store" not in cache_control:
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                await redis.set(cache_key, body.decode("utf-8", errors="ignore"), ex=settings.CACHE_TTL)
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Cache middleware SET error: %s", exc)

        return response
