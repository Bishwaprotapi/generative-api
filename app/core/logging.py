"""
Structured JSON logging configuration.
Sets up a consistent log format across the application with request-id support.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "env": settings.ENV,
            "app": settings.APP_NAME,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure root logger with JSON output on stdout."""
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # Remove any existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers in production
    if not settings.DEBUG:
        for noisy in ("httpx", "httpcore", "openai", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Convenience factory for named loggers."""
    return logging.getLogger(name)
