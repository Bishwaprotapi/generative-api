"""
v2 API router — mounts endpoint sub-routers under /v2.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import cv_v3

router = APIRouter(prefix="/v2")

# Expose the v3 cv endpoint under /api/v2/cv-parsing
router.include_router(cv_v3.router)

