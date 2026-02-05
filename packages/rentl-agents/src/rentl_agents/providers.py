"""Provider detection and tool-calling capability mapping.

This module centralizes provider detection and tool-related capability flags for
consistent handling across agent runtime and BYOK runtime.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ProviderCapabilities:
    """Tool-related capabilities for a specific provider.

    Attributes:
        name: Human-readable provider name.
        is_openrouter: Whether the provider is OpenRouter.
        supports_tool_calling: Whether tool calling is supported.
        supports_tool_choice_required: Whether tool_choice:required is supported.
    """

    name: str
    is_openrouter: bool
    supports_tool_calling: bool
    supports_tool_choice_required: bool


# Provider capability definitions
OPENROUTER_CAPABILITIES = ProviderCapabilities(
    name="OpenRouter",
    is_openrouter=True,
    supports_tool_calling=True,
    supports_tool_choice_required=True,
)

OPENAI_CAPABILITIES = ProviderCapabilities(
    name="OpenAI",
    is_openrouter=False,
    supports_tool_calling=True,
    supports_tool_choice_required=True,
)

# Local/self-hosted endpoints (LM Studio, etc.)
LOCAL_CAPABILITIES = ProviderCapabilities(
    name="Local/OpenResponses",
    is_openrouter=False,
    supports_tool_calling=True,
    supports_tool_choice_required=True,
)

# Generic fallback for unknown providers
GENERIC_CAPABILITIES = ProviderCapabilities(
    name="Generic OpenAI-compatible",
    is_openrouter=False,
    supports_tool_calling=True,
    # Conservative default for unknown OpenAI-compatible providers.
    supports_tool_choice_required=False,
)


def normalize_base_url(base_url: str) -> str:
    """Normalize a base URL for consistent comparison.

    Args:
        base_url: The base URL to normalize.

    Returns:
        Normalized base URL string.
    """
    # Convert to lowercase first to handle HTTP://, HTTPS://, etc.
    base_url_lower = base_url.lower()

    # Ensure URL has a scheme
    if not base_url_lower.startswith(("http://", "https://")):
        base_url = "https://" + base_url
    else:
        # Use the lowercase version for consistent handling
        base_url = base_url_lower

    parsed = urlparse(base_url)
    # Normalize: remove trailing slash
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    return normalized


def _is_private_ip(hostname: str) -> bool:
    """Check if hostname is a private/local IP address.

    Args:
        hostname: The hostname to check (e.g., "localhost", "127.0.0.1", "192.168.1.1")

    Returns:
        True if it's a private/local IP, False otherwise.
    """
    # Check for localhost variants
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return True

    # Check for local domain suffixes
    if hostname.endswith(".local") or hostname.endswith(".localhost"):
        return True

    # Check for private IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback
    except ValueError:
        # Not an IP address (probably a domain name)
        return False


def detect_provider(base_url: str) -> ProviderCapabilities:
    """Detect provider capabilities from base URL.

    Args:
        base_url: The API base URL.

    Returns:
        ProviderCapabilities for the detected provider.
    """
    normalized = normalize_base_url(base_url)

    # Check for OpenRouter
    if "openrouter.ai" in normalized:
        return OPENROUTER_CAPABILITIES

    # Check for OpenAI official API
    if normalized == "https://api.openai.com/v1" or "api.openai.com" in normalized:
        return OPENAI_CAPABILITIES

    # Check for local/localhost endpoints by hostname
    parsed = urlparse(normalized)
    hostname = parsed.hostname or ""

    if _is_private_ip(hostname):
        return LOCAL_CAPABILITIES

    # Check for localhost strings in URL (fallback)
    if any(
        local in normalized for local in ["localhost", "127.0.0.1", "0.0.0.0", ".local"]
    ):
        return LOCAL_CAPABILITIES

    # Generic fallback
    return GENERIC_CAPABILITIES


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
