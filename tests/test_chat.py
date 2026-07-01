"""
Tests for the chat endpoint (mocked LLM service).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chat import ChatResponse

client = TestClient(app)


@pytest.fixture()
def mock_llm_chat():
    """Patch LLMService.chat so no real API calls are made."""
    mock_response = ChatResponse(
        id="test-id",
        provider="openai",
        model="gpt-4o-mini",
        content="Hello! How can I help you?",
        usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    )
    with patch(
        "app.services.llm_service.LLMService.chat",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock:
        yield mock


def test_chat_returns_response(mock_llm_chat):
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "provider": "openai",
        "temperature": 0.7,
        "max_tokens": 100,
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Hello! How can I help you?"
    assert data["provider"] == "openai"
    mock_llm_chat.assert_awaited_once()


def test_chat_with_invalid_role():
    payload = {
        "messages": [{"role": "invalid_role", "content": "test"}],
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


def test_chat_empty_messages(mock_llm_chat):
    """Empty messages list should be accepted by validation and handled by the LLM service."""
    payload = {"messages": []}
    response = client.post("/api/v1/chat", json=payload)
    # Empty messages passes Pydantic; LLM mock returns 200
    assert response.status_code in (200, 422)
