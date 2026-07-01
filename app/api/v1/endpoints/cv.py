"""
CV upload endpoint — POST /cv-parsing

Accepts one or more CV files (PDF, DOC, DOCX), converts each to a
stitched base64 image, runs Gemini extraction, and returns the result
of the last processed file (matching the original Flask behaviour).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.cv_gemini_helper import (
    CIRCULAR_EXTRACTION_PROMPT,
    GeminiSession,
    convert_pdf_to_base64_image,
    process_file_to_pdf_nextjob,
)

router = APIRouter(tags=["CV"])

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post(
    "/cv-parsing",
    summary="Upload and parse CV files with Gemini",
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
async def extract_circular(
    files: list[UploadFile] = File(...),
):
    """
    Upload and process multiple CV files for extraction and analysis.
    Returns processed summary from the last file processed by Gemini.

    Supported formats: **PDF, DOCX, DOC**.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file list")

    gemini = GeminiSession()
    saved_files: list[str] = []
    saved_pdfs: list[str] = []
    result: dict | None = None

    try:
        for upload in files:
            filename = upload.filename or ""
            if not filename:
                continue

            # Save uploaded file to disk
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            content = await upload.read()
            with open(filepath, "wb") as fh:
                fh.write(content)
            saved_files.append(filepath)

            # Step 1: Convert to PDF if needed
            pdf_path = process_file_to_pdf_nextjob(filepath)
            if not pdf_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported or failed to convert file: {filename}",
                )
            saved_pdfs.append(pdf_path)

            # Step 2: PDF → base64 image
            base64_img = convert_pdf_to_base64_image(pdf_path)
            if not base64_img:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to render PDF as image: {filename}",
                )

            # Step 3: Gemini extraction
            result = gemini.call_api(CIRCULAR_EXTRACTION_PROMPT, base64_img)

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
