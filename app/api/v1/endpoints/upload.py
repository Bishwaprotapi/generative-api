"""
File upload endpoint — accepts multipart form data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_file_service
from app.schemas.file import FileUploadResponse
from app.services.file_service import FileService

router = APIRouter(tags=["Upload"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file with optional metadata",
)
async def upload_file(
    file: UploadFile = File(..., description="The file to upload"),
    prompt: str = Form(default="", description="Optional prompt text associated with the file"),
    metadata: str = Form(default="{}", description="JSON metadata string"),
    file_svc: FileService = Depends(get_file_service),
) -> FileUploadResponse:
    """
    Accept a multipart upload with:
    - **file**: the binary payload
    - **prompt**: optional text prompt for downstream AI processing
    - **metadata**: arbitrary JSON metadata
    """
    if file.size and file.size > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 50 MB limit.",
        )
    return await file_svc.save(file)
