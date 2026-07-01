"""
Application entry point.

Wires together:
- Structured logging
- CORS
- Middleware stack (RequestID → Timing → Cache)
- Exception handlers
- API routers
- Lifespan hooks (Redis init/close)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.api.v2.router import router as v2_router
from app.core.cache import close_redis, init_redis
from app.core.config import settings
from app.core.cors import add_cors_middleware
from app.core.logging import configure_logging
from app.middleware.cache import CacheMiddleware
from app.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle hooks."""
    configure_logging()
    await init_redis()
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG or settings.ENV != "production" else None,
        redoc_url="/redoc" if settings.DEBUG or settings.ENV != "production" else None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS (must be first) ──────────────────────────────────────────────────
    add_cors_middleware(app)

    # ── Middleware stack ──────────────────────────────────────────────────────
    # Note: Starlette middleware is applied in reverse order (last added = outermost)
    app.add_middleware(CacheMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(v1_router, prefix=settings.API_PREFIX)
    app.include_router(v2_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
