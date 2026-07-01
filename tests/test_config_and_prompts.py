"""
Tests for config loading and prompt rendering.
"""

from __future__ import annotations

import pytest

from app.core.config import get_settings, settings


def test_settings_singleton():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_default_provider_is_set():
    assert settings.DEFAULT_PROVIDER in {"openai", "gemini", "local"}


def test_api_prefix_starts_with_slash():
    assert settings.API_PREFIX.startswith("/")


def test_cache_ttl_is_positive():
    assert settings.CACHE_TTL > 0


def test_access_token_expire_positive():
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0


# ── Prompt service tests ──────────────────────────────────────────────────────


def test_prompt_list_not_empty():
    from app.services.prompt_service import prompt_service

    prompts = prompt_service.list_prompts()
    assert len(prompts) > 0


def test_chat_prompt_renders():
    from app.services.prompt_service import prompt_service

    system, rendered = prompt_service.render("chat", {"input": "Hello world"})
    assert "Hello world" in rendered
    assert isinstance(system, str)


def test_summarize_prompt_renders():
    from app.services.prompt_service import prompt_service

    system, rendered = prompt_service.render("summarize", {"input": "Some long text here."})
    assert "Some long text here." in rendered


def test_missing_prompt_raises():
    from app.services.prompt_service import prompt_service

    with pytest.raises(FileNotFoundError):
        prompt_service.get("nonexistent_prompt_xyz")
