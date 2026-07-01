"""
Health, readiness, and version endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.cache import get_redis
from app.schemas.common import HealthResponse, MessageResponse, VersionResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.VERSION,
        env=settings.ENV,
    )


@router.get("/ready", response_model=MessageResponse, summary="Readiness probe")
async def ready() -> MessageResponse:
    """Checks that critical dependencies (e.g. Redis) are available."""
    if settings.ENABLE_CACHE:
        redis = get_redis()
        if redis is None:
            return MessageResponse(message="degraded: redis unavailable")
    return MessageResponse(message="ready")


@router.get("/version", response_model=VersionResponse, summary="API version")
async def version() -> VersionResponse:
    return VersionResponse(version=settings.VERSION, app=settings.APP_NAME)
