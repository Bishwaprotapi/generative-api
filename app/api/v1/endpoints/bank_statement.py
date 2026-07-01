"""Bank statement extraction endpoint.

Accepts: PDF, images, DOC/DOCX via multipart upload.
Uses Gemini with credentials/gemini_keys-erp.json.
Returns: strict JSON as defined by the prompt.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.bank_gemini_erp_helper import (
    GeminiSessionERP,
    guess_image_mime,
    process_file_to_pdf,
)
from app.prompts.bank_statement_extract_prompt import BANK_STATEMENT_EXTRACTION_PROMPT

router = APIRouter(tags=["BankStatement"])

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SUPPORTED_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp"}
SUPPORTED_DOC_EXTS = {"doc", "docx"}


@router.post(
    "/bank-statement-extract",
    summary="Extract key fields from a bank statement (PDF/image/DOC/DOCX) into strict JSON",
    status_code=status.HTTP_200_OK,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {
                            "file": {
                                "type": "string",
                                "format": "binary",
                                "description": "Bank statement file (PDF, PNG, JPG, WEBP, DOC, DOCX)",
                            }
                        },
                    }
                }
            },
        }
    },
)
async def bank_statement_extract(file: UploadFile = File(...)):
    if not (file and (file.filename or "")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file")

    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", *SUPPORTED_IMAGE_EXTS, *SUPPORTED_DOC_EXTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Use PDF, PNG, JPG/JPEG, WEBP, DOC, or DOCX.",
        )

    saved_path = os.path.join(UPLOAD_FOLDER, filename)
    converted_pdf: str | None = None

    session = GeminiSessionERP()

    try:
        content = await file.read()
        with open(saved_path, "wb") as fh:
            fh.write(content)

        # PDF path route (PDF or DOC/DOCX → PDF)
        if ext == "pdf" or ext in SUPPORTED_DOC_EXTS:
            pdf_path = process_file_to_pdf(saved_path)
            if not pdf_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to convert document to PDF.",
                )
            if pdf_path != saved_path:
                converted_pdf = pdf_path

            return session.call_api_with_pdf_file(BANK_STATEMENT_EXTRACTION_PROMPT, pdf_path)

        # Image route
        mime = guess_image_mime(filename)
        if mime == "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported image type. Use PNG, JPG/JPEG, or WEBP.",
            )
        return session.call_api_with_image_bytes(BANK_STATEMENT_EXTRACTION_PROMPT, content, mime)

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    finally:
        # cleanup local files
        try:
            if os.path.exists(saved_path):
                os.remove(saved_path)
        except Exception:
            pass
        try:
            if converted_pdf and os.path.exists(converted_pdf):
                os.remove(converted_pdf)
        except Exception:
            pass

