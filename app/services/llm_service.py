"""
LLM provider service.

Provides a single unified interface over OpenAI, Gemini, and local LLMs
using LiteLLM as the abstraction layer. All provider-specific details
(keys, model names, base URLs) are sourced from application settings.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import litellm

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.chat import (
    ChatMessage,
    ChatResponse,
    CompletionResponse,
    EmbeddingResponse,
)

logger = get_logger(__name__)

# Silence LiteLLM's internal verbose output unless debug mode is on
litellm.set_verbose = settings.DEBUG


def _resolve_model(provider: str | None, model: str | None) -> tuple[str, str]:
    """
    Return (provider_name, litellm_model_string) for the given inputs.
    Falls back to DEFAULT_PROVIDER when provider is None.
    """
    resolved_provider = (provider or settings.DEFAULT_PROVIDER).lower()

    if resolved_provider == "openai":
        return "openai", model or settings.OPENAI_MODEL
    elif resolved_provider == "gemini":
        return "gemini", model or settings.GEMINI_MODEL
    elif resolved_provider == "local":
        # LiteLLM uses 'openai/' prefix for OpenAI-compatible endpoints
        local_model = model or settings.LOCAL_MODEL
        return "local", f"openai/{local_model}"
    else:
        raise ValueError(f"Unknown provider: {resolved_provider!r}")


def _build_litellm_kwargs(provider: str, model: str) -> dict[str, Any]:
    """Build provider-specific kwargs for LiteLLM calls."""
    kwargs: dict[str, Any] = {"model": model}

    if provider == "openai":
        kwargs["api_key"] = settings.OPENAI_API_KEY
    elif provider == "gemini":
        kwargs["api_key"] = settings.GEMINI_API_KEY
    elif provider == "local":
        kwargs["api_base"] = settings.LOCAL_BASE_URL
        kwargs["api_key"] = "ollama"  # LiteLLM requires some non-empty key

    return kwargs


class LLMService:
    """Provider-agnostic LLM service backed by LiteLLM."""

    async def chat(
        self,
        messages: list[ChatMessage],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResponse:
        """Single-shot chat completion; returns a structured response."""
        resolved_provider, resolved_model = _resolve_model(provider, model)
        kwargs = _build_litellm_kwargs(resolved_provider, resolved_model)

        litellm_messages = [m.model_dump() for m in messages]

        try:
            response = await litellm.acompletion(
                messages=litellm_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        except Exception as exc:
            if settings.ENABLE_FALLBACK and resolved_provider != settings.FALLBACK_PROVIDER:
                logger.warning(
                    "Primary provider %s failed (%s); falling back to %s.",
                    resolved_provider,
                    exc,
                    settings.FALLBACK_PROVIDER,
                )
                return await self.chat(
                    messages,
                    provider=settings.FALLBACK_PROVIDER,
                    model=None,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            raise

        content = response.choices[0].message.content or ""
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return ChatResponse(
            id=response.id or str(uuid.uuid4()),
            provider=resolved_provider,
            model=resolved_model,
            content=content,
            usage=usage,
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion; yields text chunks."""
        resolved_provider, resolved_model = _resolve_model(provider, model)
        kwargs = _build_litellm_kwargs(resolved_provider, resolved_model)

        litellm_messages = [m.model_dump() for m in messages]

        response = await litellm.acompletion(
            messages=litellm_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def completion(
        self,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> CompletionResponse:
        """Text completion by wrapping prompt in a user message."""
        resolved_provider, resolved_model = _resolve_model(provider, model)
        kwargs = _build_litellm_kwargs(resolved_provider, resolved_model)

        response = await litellm.acompletion(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        text = response.choices[0].message.content or ""
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return CompletionResponse(
            id=response.id or str(uuid.uuid4()),
            provider=resolved_provider,
            model=resolved_model,
            text=text,
            usage=usage,
        )

    async def completion_stream(
        self,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> AsyncGenerator[str, None]:
        """Streaming text completion."""
        resolved_provider, resolved_model = _resolve_model(provider, model)
        kwargs = _build_litellm_kwargs(resolved_provider, resolved_model)

        response = await litellm.acompletion(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def embeddings(
        self,
        input_text: str | list[str],
        provider: str | None = None,
        model: str | None = None,
    ) -> EmbeddingResponse:
        """Generate text embeddings."""
        resolved_provider, resolved_model = _resolve_model(provider, model)
        kwargs = _build_litellm_kwargs(resolved_provider, resolved_model)

        # Use a sensible default embedding model when not explicitly set
        if resolved_provider == "openai" and resolved_model == settings.OPENAI_MODEL:
            kwargs["model"] = "text-embedding-3-small"
        elif resolved_provider == "gemini" and resolved_model == settings.GEMINI_MODEL:
            kwargs["model"] = "gemini/text-embedding-004"

        texts = [input_text] if isinstance(input_text, str) else input_text
        response = await litellm.aembedding(input=texts, **kwargs)

        embeddings = [item["embedding"] for item in response.data]
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {"prompt_tokens": response.usage.prompt_tokens, "total_tokens": response.usage.total_tokens}

        return EmbeddingResponse(
            provider=resolved_provider,
            model=kwargs.get("model", resolved_model),
            embeddings=embeddings,
            usage=usage,
        )


# Module-level singleton — import and use directly in route handlers via DI
llm_service = LLMService()
