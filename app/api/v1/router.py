"""
v1 API router — mounts all endpoint sub-routers under /v1.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    chat,
    completions,
    cv,
    embeddings,
    files,
    health,
    items,
    nextjob,
    upload,
    users,
    bank_statement,
)

router = APIRouter(prefix="/v1")

router.include_router(health.router)
router.include_router(chat.router)
router.include_router(completions.router)
router.include_router(embeddings.router)
router.include_router(upload.router)
router.include_router(files.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(items.router)
router.include_router(cv.router)
router.include_router(nextjob.router)
router.include_router(bank_statement.router)
