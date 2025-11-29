"""LLM backend helpers."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from rentl_core.config.settings import get_settings


def get_default_chat_model() -> ChatOpenAI:
    """Return the default chat model configured via environment settings."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm_model,  # type: ignore[arg-type]
        api_key=settings.openai_api_key,
        base_url=settings.openai_url,  # type: ignore[arg-type]
    )
