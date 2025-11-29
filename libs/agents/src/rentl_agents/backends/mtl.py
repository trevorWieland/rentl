"""Machine Translation (MTL) backend for specialized translation models.

This module provides access to specialized translation models via OpenAI-compatible API endpoints.

The default configuration is optimized for Sugoi-14B-Ultra (JP→EN), but can be adapted for
other language pairs by modifying the system prompt and model configuration.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from rentl_core.config.settings import get_settings

# Default system prompt for Sugoi-14B-Ultra (JP→EN translation)
# This prompt is required for Sugoi models as specified in the Sugoi Toolkit documentation.
# Can be overridden via MTL_SYSTEM_PROMPT environment variable when using other pairs.
DEFAULT_MTL_SYSTEM_PROMPT = (
    "You are a professional localizer whose primary goal is to translate Japanese to English. "
    "You should use colloquial or slang or hentai vocabulary if it makes the translation more accurate. "
    "Always respond in English."
)


def get_mtl_system_prompt() -> str:
    """Return the MTL system prompt from settings or default.

    Returns:
        str: System prompt for MTL model.
    """
    settings = get_settings()
    return settings.mtl_system_prompt or DEFAULT_MTL_SYSTEM_PROMPT


def get_mtl_chat_model() -> ChatOpenAI | None:
    """Return the MTL chat model configured via environment settings.

    Returns:
        ChatOpenAI: Configured MTL model, or None if MTL is not configured.

    Notes:
        The MTL model is optional. If MTL_URL, MTL_API_KEY, or MTL_MODEL are not set
        in the environment, this function returns None and translation agents should
        fall back to direct translation using the primary LLM.
    """
    settings = get_settings()

    # Check if MTL is configured
    if not settings.mtl_url or not settings.mtl_model:
        return None

    # langchain-openai stubs lag runtime kwargs; skip type check for constructor call.
    return ChatOpenAI(
        model=settings.mtl_model,  # type: ignore[arg-type]
        api_key=settings.mtl_api_key,
        base_url=settings.mtl_url,  # type: ignore[arg-type]
    )


def is_mtl_available() -> bool:
    """Check if MTL backend is configured and available.

    Returns:
        bool: True if MTL is configured, False otherwise.
    """
    settings = get_settings()
    return bool(settings.mtl_url and settings.mtl_model)
