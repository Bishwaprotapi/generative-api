"""
Tests for the file upload endpoint.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_file(content: bytes = b"hello world", filename: str = "test.txt") -> dict:
    return {"file": (filename, io.BytesIO(content), "text/plain")}


def test_upload_returns_metadata():
    response = client.post(
        "/api/v1/upload",
        files=_make_file(),
        data={"prompt": "Summarize this", "metadata": "{}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == "test.txt"
    assert data["size"] == len(b"hello world")


def test_upload_and_retrieve():
    upload = client.post(
        "/api/v1/upload",
        files=_make_file(b"retrieve me"),
        data={"prompt": "", "metadata": "{}"},
    )
    assert upload.status_code == 201
    file_id = upload.json()["file_id"]

    get_resp = client.get(f"/api/v1/files/{file_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["file_id"] == file_id


def test_upload_and_delete():
    upload = client.post(
        "/api/v1/upload",
        files=_make_file(b"delete me"),
        data={"prompt": "", "metadata": "{}"},
    )
    file_id = upload.json()["file_id"]

    del_resp = client.delete(f"/api/v1/files/{file_id}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/v1/files/{file_id}")
    assert get_resp.status_code == 404


def test_file_not_found():
    response = client.get("/api/v1/files/nonexistent-id")
    assert response.status_code == 404
