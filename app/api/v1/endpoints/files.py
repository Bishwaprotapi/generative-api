"""
File management endpoints (retrieve, delete).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_file_service
from app.schemas.common import MessageResponse
from app.schemas.file import FileMetadata
from app.services.file_service import FileService

router = APIRouter(tags=["Files"])


@router.get(
    "/files/{file_id}",
    response_model=FileMetadata,
    summary="Get file metadata by ID",
)
async def get_file(
    file_id: str,
    file_svc: FileService = Depends(get_file_service),
) -> FileMetadata:
    meta = file_svc.get(file_id)
    if meta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return meta


@router.delete(
    "/files/{file_id}",
    response_model=MessageResponse,
    summary="Delete a file by ID",
)
async def delete_file(
    file_id: str,
    file_svc: FileService = Depends(get_file_service),
) -> MessageResponse:
    deleted = file_svc.delete(file_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return MessageResponse(message=f"File {file_id} deleted.")
