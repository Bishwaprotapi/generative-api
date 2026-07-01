"""
CV upload endpoint v3 — POST /cv-parsing (mounted under /v2)

Uses Gemini Files API (no Poppler).
PDF is uploaded directly to Gemini — no image conversion step.
DOC/DOCX still converted to PDF via LibreOffice first.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.cv_gemini_files_helper import (
    GeminiSessionV3,
    process_file_to_pdf_v3,
)
from app.prompts.nextjobz_prompt import CIRCULAR_EXTRACTION_PROMPT

router = APIRouter(tags=["CV"])

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post(
    "/cv-parsing",
    summary="Upload and parse CV files with Gemini (Files API — no Poppler)",
    status_code=status.HTTP_200_OK,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["files"],
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"},
                                "description": "One or more CV files (PDF, DOCX, DOC)",
                            }
                        },
                    }
                }
            },
        }
    },
)
async def extract_circular_v3(
    files: list[UploadFile] = File(...),
):
    """
    Upload and process multiple CV files using Gemini Files API.

    **No Poppler required** — PDF is sent directly to Gemini.
    DOC/DOCX files are still converted to PDF via LibreOffice first.

    Returns parsed JSON from the last file processed.
    Supported formats: **PDF, DOCX, DOC**.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file list")

    gemini = GeminiSessionV3()
    saved_files: list[str] = []
    saved_pdfs: list[str] = []
    result: dict | None = None

    try:
        for upload in files:
            filename = upload.filename or ""
            if not filename:
                continue

            # Step 1: Save uploaded file
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            content = await upload.read()
            with open(filepath, "wb") as fh:
                fh.write(content)
            saved_files.append(filepath)

            # Step 2: Convert DOC/DOCX → PDF if needed
            pdf_path = process_file_to_pdf_v3(filepath)
            if not pdf_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported or failed to convert file: {filename}",
                )
            if pdf_path != filepath:
                saved_pdfs.append(pdf_path)

            # Step 3: Upload PDF directly to Gemini Files API (no Poppler)
            result = gemini.call_api_with_file(CIRCULAR_EXTRACTION_PROMPT, pdf_path)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files were processed",
            )

        return result

    except HTTPException:
        raise

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Runtime error: {exc}",
        )

    finally:
        for f in saved_files:
            if os.path.exists(f):
                os.remove(f)
        for f in saved_pdfs:
            if os.path.exists(f):
                os.remove(f)
