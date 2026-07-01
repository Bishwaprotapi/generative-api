"""
File management service.

Handles saving uploaded files to the local filesystem,
retrieving metadata, and deletion.
In production, swap the local storage backend for S3 / GCS here.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.core.logging import get_logger
from app.schemas.file import FileMetadata, FileUploadResponse

logger = get_logger(__name__)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# In-memory file registry (replace with DB in production)
_registry: dict[str, FileMetadata] = {}


class FileService:
    async def save(self, file: UploadFile) -> FileUploadResponse:
        """Persist an uploaded file and return its metadata."""
        file_id = str(uuid.uuid4())
        ext = Path(file.filename or "file").suffix
        dest = UPLOAD_DIR / f"{file_id}{ext}"

        with open(dest, "wb") as fh:
            shutil.copyfileobj(file.file, fh)

        size = dest.stat().st_size
        now = datetime.now(timezone.utc)

        meta = FileMetadata(
            file_id=file_id,
            filename=file.filename or dest.name,
            content_type=file.content_type or "application/octet-stream",
            size=size,
            uploaded_at=now,
            path=str(dest),
        )
        _registry[file_id] = meta
        logger.info("Saved file %s → %s (%d bytes)", file.filename, dest, size)

        return FileUploadResponse(
            file_id=file_id,
            filename=meta.filename,
            content_type=meta.content_type,
            size=size,
            uploaded_at=now,
        )

    def get(self, file_id: str) -> FileMetadata | None:
        """Return metadata for a previously uploaded file."""
        return _registry.get(file_id)

    def delete(self, file_id: str) -> bool:
        """Delete a file from disk and the registry. Returns False if not found."""
        meta = _registry.pop(file_id, None)
        if meta is None:
            return False
        path = Path(meta.path)
        if path.exists():
            path.unlink()
            logger.info("Deleted file %s", path)
        return True


file_service = FileService()
