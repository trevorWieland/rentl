"""Provider detection and tool-calling capability mapping.

This module re-exports core provider detection from rentl_llm.providers and
adds agent-specific wrappers for tool compatibility checks and error messages.
"""

from __future__ import annotations

from rentl_llm.providers import (
    GENERIC_CAPABILITIES,
    LOCAL_CAPABILITIES,
    OPENAI_CAPABILITIES,
    OPENROUTER_CAPABILITIES,
    ProviderCapabilities,
    detect_provider,
    normalize_base_url,
)

__all__ = [
    "GENERIC_CAPABILITIES",
    "LOCAL_CAPABILITIES",
    "OPENAI_CAPABILITIES",
    "OPENROUTER_CAPABILITIES",
    "ProviderCapabilities",
    "assert_tool_compatibility",
    "build_provider_error_message",
    "check_tool_compatibility",
    "detect_provider",
    "normalize_base_url",
]


def check_tool_compatibility(
    base_url: str,
) -> tuple[bool, str]:
    """Check if tool-based structured output is compatible with the provider.

    Args:
        base_url: The API base URL.

    Returns:
        Tuple of (is_compatible, guidance_message).
    """
    capabilities = detect_provider(base_url)

    if not capabilities.supports_tool_calling:
        return False, f"{capabilities.name} does not support tool calling."

    if not capabilities.supports_tool_choice_required:
        return False, (
            f"{capabilities.name} does not support tool_choice:required. "
            "Use an endpoint/provider that supports required tool calling."
        )

    return True, f"Required tool calling is supported by {capabilities.name}."


def assert_tool_compatibility(base_url: str) -> ProviderCapabilities:
    """Validate provider compatibility for tool-only runtime behavior.

    Args:
        base_url: API base URL used for provider detection.

    Returns:
        ProviderCapabilities: The detected provider capabilities.

    Raises:
        ValueError: If provider does not support required tool calling behavior.
    """
    capabilities = detect_provider(base_url)
    is_compatible, guidance = check_tool_compatibility(base_url)
    if not is_compatible:
        raise ValueError(guidance)
    return capabilities


def build_provider_error_message(
    error_type: str,
    base_url: str,
) -> str:
    """Build an actionable error message for provider-related issues.

    Args:
        error_type: Type of error (e.g., "tool_incompatible", "tool_failure").
        base_url: The API base URL.

    Returns:
        Actionable error message with provider guidance.
    """
    capabilities = detect_provider(base_url)

    if error_type == "tool_incompatible":
        return (
            f"Provider {capabilities.name} is incompatible with tool-only runtime. "
            "Required capabilities: tool calling and tool_choice:required support. "
            f"Detected support: tool_calling={capabilities.supports_tool_calling}, "
            f"tool_choice_required={capabilities.supports_tool_choice_required}."
        )

    if error_type == "tool_failure":
        return (
            f"Tool calling failed with {capabilities.name}. "
            "Rentl requires tool-only structured output for agent execution. "
            f"Tool support: choice_required="
            f"{capabilities.supports_tool_choice_required}, "
            f"tool_calling={capabilities.supports_tool_calling}."
        )

    if error_type == "provider_detection":
        return (
            f"Detected provider: {capabilities.name}. "
            f"Base URL: {normalize_base_url(base_url)}. "
            f"OpenRouter={capabilities.is_openrouter}."
        )

    return f"Provider issue with {capabilities.name}. Base URL: {base_url}"
