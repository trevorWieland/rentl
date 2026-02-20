"""Provider detection and capability mapping.

Core provider detection logic used by the provider factory.
Higher-level wrappers (tool compatibility checks, error messages)
remain in rentl_agents.providers.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field


class ProviderCapabilities(BaseModel):
    """Tool-related capabilities for a specific provider.

    Attributes:
        name: Human-readable provider name.
        is_openrouter: Whether the provider is OpenRouter.
        supports_tool_calling: Whether tool calling is supported.
        supports_tool_choice_required: Whether tool_choice:required is supported.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Human-readable provider name")
    is_openrouter: bool = Field(description="Whether the provider is OpenRouter")
    supports_tool_calling: bool = Field(description="Whether tool calling is supported")
    supports_tool_choice_required: bool = Field(
        description="Whether tool_choice:required is supported"
    )


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

    # Generic fallback
    return GENERIC_CAPABILITIES
