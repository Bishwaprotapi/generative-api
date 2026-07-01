"""
Pydantic schemas for chat and completion requests/responses.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str | None = None
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=32768)
    stream: bool = False
    prompt_name: str | None = None
    prompt_vars: dict[str, str] | None = None


class ChatResponse(BaseModel):
    id: str
    provider: str
    model: str
    content: str
    usage: dict[str, int] | None = None


class CompletionRequest(BaseModel):
    prompt: str
    provider: str | None = None
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=32768)
    stream: bool = False


class CompletionResponse(BaseModel):
    id: str
    provider: str
    model: str
    text: str
    usage: dict[str, int] | None = None


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    provider: str | None = None
    model: str | None = None


class EmbeddingResponse(BaseModel):
    provider: str
    model: str
    embeddings: list[list[float]]
    usage: dict[str, int] | None = None
