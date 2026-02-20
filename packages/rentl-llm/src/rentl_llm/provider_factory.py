"""Centralized LLM provider/model factory.

All provider and model instantiation must go through create_model().
No call site may construct OpenAIProvider, OpenRouterProvider,
OpenAIChatModel, or OpenRouterModel directly.
"""

from __future__ import annotations

import logging
import re
from typing import Literal, cast

from pydantic import Field
from pydantic_ai import Agent
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

from rentl_llm.providers import ProviderCapabilities, detect_provider
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import OpenRouterProviderRoutingConfig
from rentl_schemas.primitives import ReasoningEffort

_log = logging.getLogger(__name__)

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
    reasoning_effort: ReasoningEffort | str | None = None,
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


class PreflightEndpoint(BaseSchema):
    """A model/endpoint combination to validate before pipeline start."""

    base_url: str = Field(..., min_length=1, description="Endpoint base URL")
    api_key: str = Field(..., min_length=1, description="API key for the provider")
    model_id: str = Field(..., min_length=1, description="Model identifier")
    phase_label: str = Field(
        ..., min_length=1, description="Pipeline phase using this endpoint"
    )
    endpoint_ref: str | None = Field(
        None, description="Endpoint reference for dedup identity"
    )
    openrouter_provider: OpenRouterProviderRoutingConfig | None = Field(
        None, description="OpenRouter provider routing config"
    )


class PreflightIssue(BaseSchema):
    """A single compatibility issue found during preflight."""

    phase_label: str = Field(
        ..., min_length=1, description="Phase where the issue was found"
    )
    model_id: str = Field(..., min_length=1, description="Model identifier")
    provider_name: str = Field(..., min_length=1, description="Detected provider name")
    message: str = Field(..., min_length=1, description="Actionable error description")


class PreflightResult(BaseSchema):
    """Result of preflight compatibility checks."""

    passed: bool = Field(..., description="Whether all checks passed")
    issues: list[PreflightIssue] = Field(
        default_factory=list, description="List of compatibility issues found"
    )


_PROBE_PROMPT = "Respond with exactly the word 'ok'."
_PROBE_TIMEOUT_S = 15.0


class _ProbeResult(BaseSchema):
    """Minimal structured output schema for provider probe requests."""

    ok: bool = Field(..., description="Whether the probe succeeded")


async def run_preflight_checks(
    endpoints: list[PreflightEndpoint],
) -> PreflightResult:
    """Validate model/provider compatibility before pipeline start.

    Runs static capability checks first, then sends a lightweight probe
    request to each endpoint to verify the provider actually supports
    structured output and tool calling.

    Args:
        endpoints: Model/endpoint combinations to validate.

    Returns:
        PreflightResult with pass/fail status and any issues found.
    """
    issues: list[PreflightIssue] = []

    for endpoint in endpoints:
        capabilities = detect_provider(endpoint.base_url)
        static_issues = _check_endpoint_compatibility(endpoint, capabilities)
        issues.extend(static_issues)
        if static_issues:
            continue
        probe_issues = await _probe_endpoint(endpoint, capabilities)
        issues.extend(probe_issues)

    return PreflightResult(passed=len(issues) == 0, issues=issues)


async def assert_preflight(endpoints: list[PreflightEndpoint]) -> None:
    """Run preflight checks and raise on failure.

    Args:
        endpoints: Model/endpoint combinations to validate.

    Raises:
        ProviderFactoryError: If any compatibility issues are found.
    """
    result = await run_preflight_checks(endpoints)
    if not result.passed:
        lines = ["Preflight compatibility check failed:"]
        for issue in result.issues:
            lines.append(
                f"  - [{issue.phase_label}] {issue.provider_name} / "
                f"{issue.model_id}: {issue.message}"
            )
        raise ProviderFactoryError("\n".join(lines))


async def _probe_endpoint(
    endpoint: PreflightEndpoint,
    capabilities: ProviderCapabilities,
) -> list[PreflightIssue]:
    """Send a lightweight probe request to verify the endpoint works.

    Uses create_model() to build a model, then runs a minimal Agent call
    with structured output to confirm the provider supports tool calling.

    Args:
        endpoint: The endpoint to probe.
        capabilities: Detected provider capabilities.

    Returns:
        List of issues found (empty if probe succeeds).

    Raises:
        ProviderFactoryError: If model creation fails validation
            (re-raised to caller).
    """
    try:
        model, settings = create_model(
            base_url=endpoint.base_url,
            api_key=endpoint.api_key,
            model_id=endpoint.model_id,
            temperature=0.0,
            timeout_s=_PROBE_TIMEOUT_S,
            max_output_tokens=16,
            openrouter_provider=endpoint.openrouter_provider,
        )
        agent = Agent(
            model,
            output_type=_ProbeResult,
            output_retries=2,
            system_prompt="You are a preflight check. Always respond positively.",
        )
        await agent.run(_PROBE_PROMPT, model_settings=settings)
    except ProviderFactoryError:
        raise
    except Exception as exc:
        _log.debug("Preflight probe failed for %s: %s", endpoint.model_id, exc)
        return [
            PreflightIssue(
                phase_label=endpoint.phase_label,
                model_id=endpoint.model_id,
                provider_name=capabilities.name,
                message=(
                    f"Preflight probe request failed: {exc}. "
                    "Verify the endpoint URL, API key, and model ID are correct "
                    "and that the provider supports tool-based structured output."
                ),
            )
        ]
    return []


def _check_endpoint_compatibility(
    endpoint: PreflightEndpoint,
    capabilities: ProviderCapabilities,
) -> list[PreflightIssue]:
    """Check a single endpoint for compatibility issues.

    Args:
        endpoint: The endpoint to check.
        capabilities: Detected provider capabilities.

    Returns:
        List of issues found (empty if compatible).
    """
    issues: list[PreflightIssue] = []

    if not capabilities.supports_tool_calling:
        issues.append(
            PreflightIssue(
                phase_label=endpoint.phase_label,
                model_id=endpoint.model_id,
                provider_name=capabilities.name,
                message=(
                    f"{capabilities.name} does not support tool calling. "
                    "Rentl requires tool-based structured output. "
                    "Use an endpoint that supports tool calling."
                ),
            )
        )

    if not capabilities.supports_tool_choice_required:
        issues.append(
            PreflightIssue(
                phase_label=endpoint.phase_label,
                model_id=endpoint.model_id,
                provider_name=capabilities.name,
                message=(
                    f"{capabilities.name} does not support tool_choice=required. "
                    "Rentl requires required tool calling for structured output. "
                    "Use an endpoint/provider that supports tool_choice=required."
                ),
            )
        )

    if capabilities.is_openrouter:
        issues.extend(_check_openrouter_constraints(endpoint, capabilities))

    return issues


def _check_openrouter_constraints(
    endpoint: PreflightEndpoint,
    capabilities: ProviderCapabilities,
) -> list[PreflightIssue]:
    """Check OpenRouter-specific constraints.

    Args:
        endpoint: The endpoint to check.
        capabilities: Detected provider capabilities.

    Returns:
        List of OpenRouter-specific issues found.
    """
    issues: list[PreflightIssue] = []

    if endpoint.openrouter_provider is None:
        issues.append(
            PreflightIssue(
                phase_label=endpoint.phase_label,
                model_id=endpoint.model_id,
                provider_name=capabilities.name,
                message=(
                    "OpenRouter endpoint missing provider routing config. "
                    "Set openrouter_provider with require_parameters=true "
                    "to ensure routed providers support all request parameters."
                ),
            )
        )
        return issues

    if not endpoint.openrouter_provider.require_parameters:
        issues.append(
            PreflightIssue(
                phase_label=endpoint.phase_label,
                model_id=endpoint.model_id,
                provider_name=capabilities.name,
                message=(
                    "OpenRouter require_parameters must be true. "
                    "Without this, OpenRouter may route to providers that "
                    "don't support tool_choice or response_format."
                ),
            )
        )

    return issues


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
    reasoning_effort: ReasoningEffort | str | None,
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
        "timeout": timeout_s,
        "openrouter_provider": _build_openrouter_provider_settings(openrouter_provider),
    }

    # Only include penalty parameters when non-default to avoid sending
    # extra parameters that trigger require_parameters filtering on OpenRouter
    if presence_penalty != 0.0:
        settings["presence_penalty"] = presence_penalty
    if frequency_penalty != 0.0:
        settings["frequency_penalty"] = frequency_penalty

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
    reasoning_effort: ReasoningEffort | str | None,
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
        "timeout": timeout_s,
    }

    # Only include penalty parameters when non-default to avoid unnecessary
    # parameters in API requests
    if presence_penalty != 0.0:
        settings["presence_penalty"] = presence_penalty
    if frequency_penalty != 0.0:
        settings["frequency_penalty"] = frequency_penalty

    effort_value = _resolve_reasoning_effort(reasoning_effort)
    if effort_value is not None:
        settings["openai_reasoning_effort"] = effort_value

    if max_output_tokens is not None:
        settings["max_tokens"] = max_output_tokens

    return model, cast(ModelSettings, settings)


def _resolve_reasoning_effort(
    effort: ReasoningEffort | str | None,
) -> _EffortLevel | None:
    """Resolve reasoning effort to a typed literal value.

    Accepts both ``ReasoningEffort`` enum instances and plain strings
    (Pydantic ``use_enum_values=True`` stores StrEnum members as ``str``).

    Returns:
        Effort level literal or None.
    """
    if effort is None:
        return None
    raw = effort.value if isinstance(effort, ReasoningEffort) else effort
    return cast(_EffortLevel, raw)


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
