"""
Application configuration loaded from environment variables via pydantic-settings.
All settings are type-validated and centrally accessible via the `settings` singleton.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "FastAPI AI Template"
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    VERSION: str = "1.0.0"

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── LLM Provider ─────────────────────────────────────────────────────────
    DEFAULT_PROVIDER: Literal["openai", "gemini", "local"] = "openai"
    ENABLE_STREAMING: bool = True
    ENABLE_FALLBACK: bool = False
    FALLBACK_PROVIDER: Literal["openai", "gemini", "local"] = "openai"

    # ── OpenAI ───────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Gemini ───────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini/gemini-2.5-flash"

    # ── Local LLM (Ollama / OpenAI-compatible) ───────────────────────────────
    LOCAL_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_MODEL: str = "llama3.2"

    # ── Caching ───────────────────────────────────────────────────────────────
    ENABLE_CACHE: bool = False
    CACHE_BACKEND: Literal["redis", "memory"] = "redis"
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # seconds

    # ── Prompts ───────────────────────────────────────────────────────────────
    PROMPT_DIR: str = "app/prompts"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()


settings: Settings = get_settings()
