"""Tests for bank statement extraction endpoint.

We monkeypatch the Gemini session methods so tests don't require
network access or valid API keys.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.main import app


def _make_upload(filename: str, content: bytes, content_type: str) -> dict:
    return {"file": (filename, io.BytesIO(content), content_type)}


def test_bank_statement_rejects_unsupported_type():
    client = TestClient(app)
    resp = client.post(
        "/api/v1/bank-statement-extract",
        files=_make_upload("statement.txt", b"hello", "text/plain"),
    )
    assert resp.status_code == 400


def test_bank_statement_pdf_happy_path(monkeypatch):
    # Patch away GeminiSessionERP __init__ to avoid reading keys file.
    from app.api.v1.endpoints import bank_statement as endpoint
    from app import bank_gemini_erp_helper as helper

    monkeypatch.setattr(helper.GeminiSessionERP, "__init__", lambda self: None)

    expected = {
        "Account_Number": "123",
        "Account_Name": "ACME LTD",
        "Opening_Balance": 1000,
        "Closing_Balance": 900,
        "Bank_Name": "Test Bank",
        "Bank_Branch": "Main",
        "Statement_Genaration_Date": "2026-05-14",
        "Client_Address": "Addr",
    }

    monkeypatch.setattr(
        helper.GeminiSessionERP,
        "call_api_with_pdf_file",
        lambda self, prompt, pdf_path: expected,
    )

    client = TestClient(app)
    resp = client.post(
        "/api/v1/bank-statement-extract",
        files=_make_upload("statement.pdf", b"%PDF-1.4 fake", "application/pdf"),
    )
    assert resp.status_code == 200
    assert resp.json() == expected


def test_bank_statement_image_happy_path(monkeypatch):
    from app import bank_gemini_erp_helper as helper

    monkeypatch.setattr(helper.GeminiSessionERP, "__init__", lambda self: None)

    expected = {
        "Account_Number": "",
        "Account_Name": "John Doe",
        "Opening_Balance": 0,
        "Closing_Balance": 0,
        "Bank_Name": "",
        "Bank_Branch": "",
        "Statement_Genaration_Date": "",
        "Client_Address": "",
    }

    monkeypatch.setattr(
        helper.GeminiSessionERP,
        "call_api_with_image_bytes",
        lambda self, prompt, image_bytes, mime_type: expected,
    )

    client = TestClient(app)
    resp = client.post(
        "/api/v1/bank-statement-extract",
        files=_make_upload("statement.png", b"\x89PNG\r\n\x1a\nFAKE", "image/png"),
    )
    assert resp.status_code == 200
    assert resp.json() == expected

