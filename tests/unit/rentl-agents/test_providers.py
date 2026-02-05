"""Tests for provider detection and tool-only compatibility mapping."""

from __future__ import annotations

import pytest

from rentl_agents.providers import (
    GENERIC_CAPABILITIES,
    LOCAL_CAPABILITIES,
    OPENAI_CAPABILITIES,
    OPENROUTER_CAPABILITIES,
    assert_tool_compatibility,
    build_provider_error_message,
    check_tool_compatibility,
    detect_provider,
    normalize_base_url,
)


class TestNormalizeBaseUrl:
    """Tests for base URL normalization."""

    def test_normalizes_trailing_slash(self) -> None:
        """Trailing slash is removed from normalized URLs."""
        assert (
            normalize_base_url("https://api.openai.com/v1/")
            == "https://api.openai.com/v1"
        )

    def test_adds_https_scheme(self) -> None:
        """URLs without scheme default to HTTPS."""
        assert normalize_base_url("api.openai.com/v1") == "https://api.openai.com/v1"

    def test_preserves_http_scheme(self) -> None:
        """HTTP URLs are preserved for local endpoints."""
        assert (
            normalize_base_url("http://localhost:8000/v1") == "http://localhost:8000/v1"
        )

    def test_converts_to_lowercase(self) -> None:
        """Normalization lowercases URLs for stable matching."""
        assert (
            normalize_base_url("HTTPS://API.OPENAI.COM/V1")
            == "https://api.openai.com/v1"
        )


class TestDetectProvider:
    """Tests for provider detection from base URL."""

    def test_detects_openrouter(self) -> None:
        """OpenRouter host is detected with OpenRouter capabilities."""
        caps = detect_provider("https://openrouter.ai/api/v1")
        assert caps == OPENROUTER_CAPABILITIES
        assert caps.is_openrouter is True

    def test_detects_openai(self) -> None:
        """OpenAI host is detected with OpenAI capabilities."""
        caps = detect_provider("https://api.openai.com/v1")
        assert caps == OPENAI_CAPABILITIES
        assert caps.is_openrouter is False

    def test_detects_localhost(self) -> None:
        """Localhost URLs map to local provider capabilities."""
        caps = detect_provider("http://localhost:8000/v1")
        assert caps == LOCAL_CAPABILITIES

    def test_detects_private_ips_as_local(self) -> None:
        """Private and loopback IPs map to local capabilities."""
        assert detect_provider("http://127.0.0.1:8000/v1") == LOCAL_CAPABILITIES
        assert detect_provider("http://10.0.0.5:1234/v1") == LOCAL_CAPABILITIES
        assert detect_provider("http://192.168.1.100:8000/v1") == LOCAL_CAPABILITIES

    def test_detects_generic(self) -> None:
        """Unknown hosts map to generic OpenAI-compatible capabilities."""
        caps = detect_provider("https://unknown.api.com/v1")
        assert caps == GENERIC_CAPABILITIES


class TestToolCompatibility:
    """Tests for tool-only compatibility checks."""

    def test_openrouter_is_tool_compatible(self) -> None:
        """OpenRouter is accepted for tool-only execution."""
        compatible, guidance = check_tool_compatibility("https://openrouter.ai/api/v1")
        assert compatible is True
        assert "supported" in guidance

    def test_openai_is_tool_compatible(self) -> None:
        """OpenAI is accepted for tool-only execution."""
        compatible, guidance = check_tool_compatibility("https://api.openai.com/v1")
        assert compatible is True
        assert "supported" in guidance

    def test_unknown_generic_provider_is_not_tool_compatible(self) -> None:
        """Unknown providers fail strict tool-choice compatibility checks."""
        compatible, guidance = check_tool_compatibility("https://unknown.api.com/v1")
        assert compatible is False
        assert "tool_choice:required" in guidance

    def test_assert_tool_compatibility_raises_for_generic(self) -> None:
        """Assertion helper raises for incompatible providers."""
        with pytest.raises(ValueError) as exc_info:
            assert_tool_compatibility("https://unknown.api.com/v1")
        assert "tool_choice:required" in str(exc_info.value)


class TestBuildProviderErrorMessage:
    """Tests for provider error message building."""

    def test_tool_incompatible_message(self) -> None:
        """Tool-incompatible message includes capability details."""
        msg = build_provider_error_message(
            "tool_incompatible",
            "https://unknown.api.com/v1",
        )
        assert "incompatible with tool-only runtime" in msg
        assert "tool_choice_required=False" in msg

    def test_tool_failure_message(self) -> None:
        """Tool failure message references tool-only requirements."""
        msg = build_provider_error_message(
            "tool_failure",
            "https://openrouter.ai/api/v1",
        )
        assert "OpenRouter" in msg
        assert "tool-only" in msg

    def test_provider_detection_message(self) -> None:
        """Provider detection message includes OpenRouter detection status."""
        msg = build_provider_error_message(
            "provider_detection",
            "https://openrouter.ai/api/v1",
        )
        assert "OpenRouter" in msg
        assert "OpenRouter=True" in msg
