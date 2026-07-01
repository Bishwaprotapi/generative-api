"""
Tests for the health endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "app" in data


def test_ready_endpoint():
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert "message" in response.json()


def test_version_endpoint():
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "app" in data


def test_request_id_header_present():
    response = client.get("/api/v1/health")
    assert "x-request-id" in response.headers


def test_process_time_header_present():
    response = client.get("/api/v1/health")
    assert "x-process-time-ms" in response.headers
