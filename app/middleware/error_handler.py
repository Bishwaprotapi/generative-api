"""
Global exception-handling middleware.

Converts unhandled exceptions into consistent JSON error responses
so clients always receive a structured payload regardless of error type.
"""

from __future__ import annotations

import traceback

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


def _error_response(code: str, message: str, details=None, status_code: int = 500) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error_response(
        code=f"HTTP_{exc.status_code}",
        message=exc.detail,
        status_code=exc.status_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=exc.errors(),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.error(
        "Unhandled exception [request_id=%s]: %s\n%s",
        request_id,
        exc,
        traceback.format_exc(),
    )
    return _error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
