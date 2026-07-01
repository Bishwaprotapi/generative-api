"""
pytest configuration and shared fixtures.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_file_registry():
    """Ensure each test starts with a clean file registry."""
    from app.services import file_service as fs_module

    fs_module._registry.clear()
    yield
    fs_module._registry.clear()
