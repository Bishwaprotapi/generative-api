"""
CORS middleware registration.
Origins are driven by CORS_ORIGINS in the environment.

Note on credentials:
- Browsers disallow Access-Control-Allow-Origin: * when credentials are used.
- If you truly want "allow all" and also want cookies/Authorization, set allow_origin_regex=".*"
  so Starlette echoes the request Origin.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def add_cors_middleware(app: FastAPI) -> None:
    """Attach CORSMiddleware.

    Default settings already use CORS_ORIGINS=['*'].
    This function additionally handles the common wildcard+credentials case.
    """

    allow_all = any(origin == "*" for origin in settings.CORS_ORIGINS)

    app.add_middleware(
        CORSMiddleware,
        # If allow-all, use regex to echo any Origin (works with credentials).
        allow_origins=[] if allow_all else settings.CORS_ORIGINS,
        allow_origin_regex=".*" if allow_all else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,
    )
