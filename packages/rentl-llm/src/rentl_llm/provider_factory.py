"""Centralized LLM provider/model factory.

All provider and model instantiation must go through create_model().
No call site may construct OpenAIProvider, OpenRouterProvider,
OpenAIChatModel, or OpenRouterModel directly.
"""

from __future__ import annotations

import re
from typing import Literal, cast

from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.models.openrouter import (
    OpenRouterModel,
    OpenRouterModelSettings,
    OpenRouterProviderConfig,
)
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.settings import ModelSettings

from rentl_agents.providers import detect_provider
from rentl_schemas.config import OpenRouterProviderRoutingConfig
from rentl_schemas.primitives import ReasoningEffort

_OPENROUTER_MODEL_ID_RE = re.compile(r"^[^/]+/.+")
_EffortLevel = Literal["low", "medium", "high"]


class ProviderFactoryError(Exception):
    """Raised when provider/model creation fails validation."""


def create_model(
    *,
    base_url: str,
    api_key: str,
    model_id: str,
    temperature: float,
    top_p: float = 1.0,
    timeout_s: float = 60.0,
    max_output_tokens: int | None = None,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
    reasoning_effort: ReasoningEffort | None = None,
    openrouter_provider: OpenRouterProviderRoutingConfig | None = None,
) -> tuple[Model, ModelSettings]:
    """Create the correct provider/model pair from configuration.

    Routes OpenRouter vs generic OpenAI based on detect_provider().
    Validates model IDs and enforces provider allowlists for OpenRouter.

    Args:
        base_url: Endpoint base URL.
        api_key: API key for the provider.
        model_id: Model identifier.
        temperature: Sampling temperature.
        top_p: Top-p sampling.
        timeout_s: Request timeout in seconds.
        max_output_tokens: Maximum output tokens (None uses model default).
        presence_penalty: Presence penalty.
        frequency_penalty: Frequency penalty.
        reasoning_effort: Reasoning effort level when supported.
        openrouter_provider: OpenRouter provider routing config.

    Returns:
        Tuple of (Model, ModelSettings) ready for pydantic-ai Agent.
    """
    capabilities = detect_provider(base_url)

    if capabilities.is_openrouter:
        return _create_openrouter_model(
            api_key=api_key,
            model_id=model_id,
            temperature=temperature,
            top_p=top_p,
            timeout_s=timeout_s,
            max_output_tokens=max_output_tokens,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            reasoning_effort=reasoning_effort,
            openrouter_provider=openrouter_provider,
        )
    return _create_openai_model(
        base_url=base_url,
        api_key=api_key,
        model_id=model_id,
        temperature=temperature,
        top_p=top_p,
        timeout_s=timeout_s,
        max_output_tokens=max_output_tokens,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        reasoning_effort=reasoning_effort,
    )


def validate_openrouter_model_id(model_id: str) -> None:
    """Validate an OpenRouter model ID matches the required format.

    OpenRouter model IDs must be in the form 'provider/model-name'.

    Args:
        model_id: The model ID to validate.

    Raises:
        ProviderFactoryError: If the model ID is invalid.
    """
    if not _OPENROUTER_MODEL_ID_RE.match(model_id):
        raise ProviderFactoryError(
            f"Invalid OpenRouter model ID '{model_id}': "
            "must match format 'provider/model-name' (e.g. 'openai/gpt-4o')"
        )


def enforce_provider_allowlist(
    model_id: str,
    openrouter_provider: OpenRouterProviderRoutingConfig | None,
) -> None:
    """Enforce the provider allowlist against a model ID.

    When the 'only' field is configured, the model's provider prefix
    must appear in the allowlist.

    Args:
        model_id: The model ID (must be valid OpenRouter format).
        openrouter_provider: OpenRouter routing config (may be None).

    Raises:
        ProviderFactoryError: If the model's provider is not in the allowlist.
    """
    if openrouter_provider is None or openrouter_provider.only is None:
        return
    provider_prefix = model_id.split("/", 1)[0]
    if provider_prefix not in openrouter_provider.only:
        allowed = ", ".join(openrouter_provider.only)
        raise ProviderFactoryError(
            f"Model provider '{provider_prefix}' is not in the allowlist. "
            f"Allowed providers: {allowed}"
        )


def _create_openrouter_model(
    *,
    api_key: str,
    model_id: str,
    temperature: float,
    top_p: float,
    timeout_s: float,
    max_output_tokens: int | None,
    presence_penalty: float,
    frequency_penalty: float,
    reasoning_effort: ReasoningEffort | None,
    openrouter_provider: OpenRouterProviderRoutingConfig | None,
) -> tuple[Model, ModelSettings]:
    """Create an OpenRouter model and settings.

    Returns:
        Tuple of (Model, ModelSettings) for OpenRouter.
    """
    validate_openrouter_model_id(model_id)
    enforce_provider_allowlist(model_id, openrouter_provider)

    provider = OpenRouterProvider(api_key=api_key)
    model = OpenRouterModel(model_id, provider=provider)

    settings: OpenRouterModelSettings = {
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "timeout": timeout_s,
        "openrouter_provider": _build_openrouter_provider_settings(openrouter_provider),
    }

    effort_value = _resolve_reasoning_effort(reasoning_effort)
    if effort_value is not None:
        settings["openrouter_reasoning"] = {"effort": effort_value}

    if max_output_tokens is not None:
        settings["max_tokens"] = max_output_tokens

    return model, cast(ModelSettings, settings)


def _create_openai_model(
    *,
    base_url: str,
    api_key: str,
    model_id: str,
    temperature: float,
    top_p: float,
    timeout_s: float,
    max_output_tokens: int | None,
    presence_penalty: float,
    frequency_penalty: float,
    reasoning_effort: ReasoningEffort | None,
) -> tuple[Model, ModelSettings]:
    """Create a generic OpenAI-compatible model and settings.

    Returns:
        Tuple of (Model, ModelSettings) for OpenAI-compatible endpoint.
    """
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    model = OpenAIChatModel(model_id, provider=provider)

    settings: OpenAIChatModelSettings = {
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "timeout": timeout_s,
    }

    effort_value = _resolve_reasoning_effort(reasoning_effort)
    if effort_value is not None:
        settings["openai_reasoning_effort"] = effort_value

    if max_output_tokens is not None:
        settings["max_tokens"] = max_output_tokens

    return model, cast(ModelSettings, settings)


def _resolve_reasoning_effort(effort: ReasoningEffort | None) -> _EffortLevel | None:
    """Resolve reasoning effort to a typed literal value.

    Returns:
        Effort level literal or None.
    """
    if effort is None:
        return None
    return cast(_EffortLevel, effort.value)


def _build_openrouter_provider_settings(
    config: OpenRouterProviderRoutingConfig | None,
) -> OpenRouterProviderConfig:
    """Build OpenRouter provider routing settings with safe defaults.

    Returns:
        OpenRouterProviderConfig payload.
    """
    resolved = config or OpenRouterProviderRoutingConfig(require_parameters=True)
    payload = resolved.model_dump(mode="python", exclude_none=True)
    return cast(OpenRouterProviderConfig, payload)
