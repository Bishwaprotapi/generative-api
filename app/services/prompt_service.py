"""
Prompt management service.

Loads YAML prompt definitions from disk, caches them in memory,
and renders templates with Jinja2.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, Undefined, TemplateError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PromptTemplate:
    """Holds a parsed prompt definition from a YAML file."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.name: str = data["name"]
        self.system: str = data.get("system", "")
        self.template: str = data["template"]
        self.temperature: float = data.get("temperature", 0.7)
        self.max_tokens: int = data.get("max_tokens", 1024)
        self.top_p: float = data.get("top_p", 1.0)
        self.provider_override: str | None = data.get("provider_override")

        # Use Undefined (not StrictUndefined) so optional variables in
        # {% if context %} blocks don't raise when the key is absent.
        self._jinja_env = Environment(undefined=Undefined, autoescape=False)
        self._tmpl = self._jinja_env.from_string(self.template)

    def render(self, variables: dict[str, Any]) -> str:
        """Render the template with the provided variables."""
        try:
            return self._tmpl.render(**variables)
        except TemplateError as exc:
            raise ValueError(f"Template rendering failed for '{self.name}': {exc}") from exc


class PromptService:
    """Loads and caches prompt templates from the configured YAML directory."""

    def __init__(self) -> None:
        self._cache: dict[str, PromptTemplate] = {}
        self._prompt_dir = Path(settings.PROMPT_DIR)

    def _load(self, name: str) -> PromptTemplate:
        """Load a prompt YAML by name, with in-memory caching."""
        if name in self._cache:
            return self._cache[name]

        path = self._prompt_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt '{name}' not found at {path}")

        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        tmpl = PromptTemplate(data)
        self._cache[name] = tmpl
        logger.debug("Loaded prompt template: %s", name)
        return tmpl

    def get(self, name: str) -> PromptTemplate:
        """Return a PromptTemplate by name."""
        return self._load(name)

    def render(self, name: str, variables: dict[str, Any]) -> tuple[str, str]:
        """
        Render a named template with the given variables.
        Returns (system_prompt, rendered_user_message).
        """
        tmpl = self._load(name)
        return tmpl.system, tmpl.render(variables)

    def list_prompts(self) -> list[str]:
        """Return names of all available prompt YAML files."""
        if not self._prompt_dir.exists():
            return []
        return [
            p.stem
            for p in self._prompt_dir.iterdir()
            if p.suffix in {".yaml", ".yml"}
        ]

    def invalidate(self, name: str | None = None) -> None:
        """Clear cached templates (all or a specific one)."""
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()


prompt_service = PromptService()
