"""Coverage for backend stubs (MTL config/overrides) and graph placeholders."""

from __future__ import annotations

import importlib
from collections.abc import Generator

import pytest
from rentl_agents.backends import mtl as mtl_backend
from rentl_agents.graph import engine
from rentl_core.config.settings import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Clear cached settings between tests and ensure required base env."""
    # Minimal required env for settings validation
    monkeypatch.setenv("OPENAI_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_mtl_prompt_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """MTL system prompt should honor env override and fallback to default."""
    custom_prompt = "Use this prompt instead"
    monkeypatch.setenv("MTL_SYSTEM_PROMPT", custom_prompt)
    get_settings.cache_clear()
    assert mtl_backend.get_mtl_system_prompt() == custom_prompt

    monkeypatch.delenv("MTL_SYSTEM_PROMPT", raising=False)
    get_settings.cache_clear()
    assert mtl_backend.get_mtl_system_prompt() == mtl_backend.DEFAULT_MTL_SYSTEM_PROMPT


def test_mtl_availability_and_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """MTL availability flags and chat model creation should reflect env."""
    # Missing MTL_URL/MTL_MODEL => unavailable
    monkeypatch.setenv("MTL_URL", "")
    monkeypatch.setenv("MTL_MODEL", "")
    monkeypatch.setenv("MTL_API_KEY", "")
    get_settings.cache_clear()
    assert mtl_backend.is_mtl_available() is False
    assert mtl_backend.get_mtl_chat_model() is None

    # Configure MTL and ensure chat model is constructed
    monkeypatch.setenv("MTL_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("MTL_MODEL", "mtl-model")
    monkeypatch.setenv("MTL_API_KEY", "mtl-key")
    get_settings.cache_clear()
    assert mtl_backend.is_mtl_available() is True
    model = mtl_backend.get_mtl_chat_model()
    assert model is not None
    model_name = getattr(model, "model_name", getattr(model, "model", None))
    assert model_name == "mtl-model"


def test_graph_engine_exports_are_available() -> None:
    """Placeholder graph/engine exports should remain importable."""
    # Reload to ensure coverage and __all__ wiring
    importlib.reload(engine)
    for name in engine.__all__:
        attr = getattr(engine, name, None)
        assert attr is not None, f"Expected {name} to be exported from engine"
