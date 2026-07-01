"""
Pydantic schemas for file upload/management.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime


class FileMetadata(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime
    path: str
