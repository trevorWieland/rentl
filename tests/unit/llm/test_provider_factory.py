"""Unit tests for LLM provider factory."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.models.openrouter import OpenRouterModelSettings

from rentl_agents.providers import ProviderCapabilities
from rentl_llm.provider_factory import (
    PreflightEndpoint,
    ProviderFactoryError,
    assert_preflight,
    create_model,
    enforce_provider_allowlist,
    run_preflight_checks,
    validate_openrouter_model_id,
)
from rentl_schemas.config import OpenRouterProviderRoutingConfig
from rentl_schemas.primitives import ReasoningEffort


class TestCreateModelOpenRouterRouting:
    """Tests for OpenRouter routing path."""

    @patch("rentl_llm.provider_factory.OpenRouterProvider")
    @patch("rentl_llm.provider_factory.OpenRouterModel")
    def test_openrouter_url_creates_openrouter_model(
        self,
        mock_model_cls: MagicMock,
        mock_provider_cls: MagicMock,
    ) -> None:
        """OpenRouter base URL routes to OpenRouterModel."""
        model, settings = create_model(
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model_id="openai/gpt-4o",
            temperature=0.5,
        )
        mock_model_cls.assert_called_once()
        mock_provider_cls.assert_called_once_with(api_key="test-key")
        assert model is mock_model_cls.return_value
        assert settings["temperature"] == 0.5
        assert "openrouter_provider" in settings

    @patch("rentl_llm.provider_factory.OpenRouterProvider")
    @patch("rentl_llm.provider_factory.OpenRouterModel")
    def test_openrouter_includes_reasoning_effort(
        self,
        mock_model_cls: MagicMock,
        mock_provider_cls: MagicMock,
    ) -> None:
        """OpenRouter path includes reasoning effort when set."""
        _, settings = create_model(
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model_id="openai/gpt-4o",
            temperature=0.5,
        )
        assert "openrouter_reasoning" not in settings

        _, settings = create_model(
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model_id="openai/gpt-4o",
            temperature=0.5,
            reasoning_effort=ReasoningEffort.HIGH,
        )
        or_settings = cast(OpenRouterModelSettings, settings)
        assert or_settings["openrouter_reasoning"] == {"effort": "high"}
        mock_model_cls.assert_called()
        mock_provider_cls.assert_called()

    @patch("rentl_llm.provider_factory.OpenRouterProvider")
    @patch("rentl_llm.provider_factory.OpenRouterModel")
    def test_openrouter_includes_max_tokens(
        self,
        mock_model_cls: MagicMock,
        mock_provider_cls: MagicMock,
    ) -> None:
        """OpenRouter path includes max_tokens when set."""
        _, settings = create_model(
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            model_id="openai/gpt-4o",
            temperature=0.5,
            max_output_tokens=2048,
        )
        assert settings["max_tokens"] == 2048
        mock_model_cls.assert_called_once()
        mock_provider_cls.assert_called_once()


class TestCreateModelOpenAIRouting:
    """Tests for generic OpenAI routing path."""

    @patch("rentl_llm.provider_factory.OpenAIProvider")
    @patch("rentl_llm.provider_factory.OpenAIChatModel")
    def test_openai_url_creates_openai_model(
        self,
        mock_model_cls: MagicMock,
        mock_provider_cls: MagicMock,
    ) -> None:
        """Generic OpenAI base URL routes to OpenAIChatModel."""
        model, settings = create_model(
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model_id="gpt-4o",
            temperature=0.3,
        )
        mock_model_cls.assert_called_once()
        mock_provider_cls.assert_called_once_with(
            base_url="https://api.openai.com/v1", api_key="test-key"
        )
        assert model is mock_model_cls.return_value
        assert settings["temperature"] == 0.3
        assert "openrouter_provider" not in settings

    @patch("rentl_llm.provider_factory.OpenAIProvider")
    @patch("rentl_llm.provider_factory.OpenAIChatModel")
    def test_local_url_creates_openai_model(
        self,
        mock_model_cls: MagicMock,
        mock_provider_cls: MagicMock,
    ) -> None:
        """Local base URL routes to OpenAIChatModel."""
        model, _ = create_model(
            base_url="http://localhost:8080/v1",
            api_key="test-key",
            model_id="local-model",
            temperature=0.5,
        )
        mock_model_cls.assert_called_once()
        assert model is mock_model_cls.return_value

    @patch("rentl_llm.provider_factory.OpenAIProvider")
    @patch("rentl_llm.provider_factory.OpenAIChatModel")
    def test_openai_includes_reasoning_effort(
        self,
        mock_model_cls: MagicMock,
        mock_provider_cls: MagicMock,
    ) -> None:
        """OpenAI path includes reasoning effort when set."""
        _, settings = create_model(
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model_id="gpt-4o",
            temperature=0.5,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        oai_settings = cast(OpenAIChatModelSettings, settings)
        assert oai_settings["openai_reasoning_effort"] == "medium"
        mock_model_cls.assert_called_once()
        mock_provider_cls.assert_called_once()


class TestModelIdValidation:
    """Tests for OpenRouter model ID validation."""

    def test_valid_model_id_passes(self) -> None:
        """Valid provider/model format passes validation."""
        validate_openrouter_model_id("openai/gpt-4o")
        validate_openrouter_model_id("anthropic/claude-3-opus")
        validate_openrouter_model_id("meta-llama/llama-3-70b-instruct")

    def test_invalid_model_id_no_slash_fails(self) -> None:
        """Model ID without slash fails validation."""
        with pytest.raises(ProviderFactoryError, match="Invalid OpenRouter model ID"):
            validate_openrouter_model_id("gpt-4o")

    def test_invalid_model_id_empty_fails(self) -> None:
        """Empty model ID fails validation."""
        with pytest.raises(ProviderFactoryError, match="Invalid OpenRouter model ID"):
            validate_openrouter_model_id("")

    def test_invalid_model_id_slash_only_fails(self) -> None:
        """Model ID with only slash fails validation."""
        with pytest.raises(ProviderFactoryError, match="Invalid OpenRouter model ID"):
            validate_openrouter_model_id("/model")

    def test_create_model_rejects_invalid_openrouter_id(self) -> None:
        """create_model rejects invalid OpenRouter model IDs."""
        with pytest.raises(ProviderFactoryError, match="Invalid OpenRouter model ID"):
            create_model(
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
                model_id="no-slash",
                temperature=0.5,
            )


class TestProviderAllowlist:
    """Tests for provider allowlist enforcement."""

    def test_allowlist_permits_listed_provider(self) -> None:
        """Model from an allowed provider passes."""
        config = OpenRouterProviderRoutingConfig(
            only=["openai", "anthropic"],
        )
        enforce_provider_allowlist("openai/gpt-4o", config)

    def test_allowlist_blocks_unlisted_provider(self) -> None:
        """Model from a provider not in the allowlist is rejected."""
        config = OpenRouterProviderRoutingConfig(
            only=["openai"],
        )
        with pytest.raises(ProviderFactoryError, match="not in the allowlist"):
            enforce_provider_allowlist("anthropic/claude-3-opus", config)

    def test_no_allowlist_permits_all(self) -> None:
        """When only is None, all providers are permitted."""
        config = OpenRouterProviderRoutingConfig()
        enforce_provider_allowlist("anything/model", config)

    def test_none_config_permits_all(self) -> None:
        """When config is None, all providers are permitted."""
        enforce_provider_allowlist("anything/model", None)

    @patch("rentl_llm.provider_factory.OpenRouterProvider")
    @patch("rentl_llm.provider_factory.OpenRouterModel")
    def test_create_model_enforces_allowlist(
        self,
        mock_model_cls: MagicMock,
        mock_provider_cls: MagicMock,
    ) -> None:
        """create_model enforces the provider allowlist end-to-end."""
        config = OpenRouterProviderRoutingConfig(only=["openai"])
        with pytest.raises(ProviderFactoryError, match="not in the allowlist"):
            create_model(
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
                model_id="anthropic/claude-3-opus",
                temperature=0.5,
                openrouter_provider=config,
            )
        mock_model_cls.assert_not_called()
        mock_provider_cls.assert_not_called()


class TestPreflightChecks:
    """Tests for preflight compatibility checks."""

    def test_compatible_openai_endpoint_passes(self) -> None:
        """OpenAI endpoint with tool support passes preflight."""
        endpoints = [
            PreflightEndpoint(
                base_url="https://api.openai.com/v1",
                model_id="gpt-4o",
                phase_label="translate",
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is True
        assert result.issues == []

    def test_compatible_openrouter_endpoint_passes(self) -> None:
        """OpenRouter endpoint with require_parameters passes preflight."""
        endpoints = [
            PreflightEndpoint(
                base_url="https://openrouter.ai/api/v1",
                model_id="openai/gpt-4o",
                phase_label="translate",
                openrouter_provider=OpenRouterProviderRoutingConfig(
                    require_parameters=True,
                ),
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is True
        assert result.issues == []

    @patch("rentl_llm.provider_factory.detect_provider")
    def test_no_tool_calling_fails(self, mock_detect: MagicMock) -> None:
        """Provider without tool calling fails preflight."""
        mock_detect.return_value = ProviderCapabilities(
            name="NoToolProvider",
            is_openrouter=False,
            supports_tool_calling=False,
            supports_tool_choice_required=False,
        )
        endpoints = [
            PreflightEndpoint(
                base_url="https://example.com/v1",
                model_id="some-model",
                phase_label="translate",
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is False
        assert len(result.issues) == 2
        messages = [issue.message for issue in result.issues]
        assert any("tool calling" in m for m in messages)
        assert any("tool_choice=required" in m for m in messages)
        mock_detect.assert_called_once_with("https://example.com/v1")

    @patch("rentl_llm.provider_factory.detect_provider")
    def test_no_tool_choice_required_fails(self, mock_detect: MagicMock) -> None:
        """Provider without tool_choice=required fails preflight."""
        mock_detect.return_value = ProviderCapabilities(
            name="LimitedProvider",
            is_openrouter=False,
            supports_tool_calling=True,
            supports_tool_choice_required=False,
        )
        endpoints = [
            PreflightEndpoint(
                base_url="https://example.com/v1",
                model_id="some-model",
                phase_label="qa",
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is False
        assert len(result.issues) == 1
        assert "tool_choice=required" in result.issues[0].message
        assert result.issues[0].phase_label == "qa"
        assert result.issues[0].provider_name == "LimitedProvider"
        mock_detect.assert_called_once()

    def test_openrouter_missing_provider_config_fails(self) -> None:
        """OpenRouter endpoint without provider routing config fails."""
        endpoints = [
            PreflightEndpoint(
                base_url="https://openrouter.ai/api/v1",
                model_id="openai/gpt-4o",
                phase_label="context",
                openrouter_provider=None,
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is False
        assert len(result.issues) == 1
        assert "missing provider routing config" in result.issues[0].message

    @patch("rentl_llm.provider_factory.detect_provider")
    def test_openrouter_require_parameters_false_fails(
        self, mock_detect: MagicMock
    ) -> None:
        """OpenRouter endpoint with require_parameters=false fails."""
        mock_detect.return_value = ProviderCapabilities(
            name="OpenRouter",
            is_openrouter=True,
            supports_tool_calling=True,
            supports_tool_choice_required=True,
        )
        endpoints = [
            PreflightEndpoint(
                base_url="https://openrouter.ai/api/v1",
                model_id="openai/gpt-4o",
                phase_label="edit",
                openrouter_provider=OpenRouterProviderRoutingConfig(
                    require_parameters=False,
                ),
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is False
        assert len(result.issues) == 1
        assert "require_parameters must be true" in result.issues[0].message
        mock_detect.assert_called_once()

    def test_multiple_endpoints_all_compatible(self) -> None:
        """Multiple compatible endpoints all pass."""
        endpoints = [
            PreflightEndpoint(
                base_url="https://api.openai.com/v1",
                model_id="gpt-4o",
                phase_label="translate",
            ),
            PreflightEndpoint(
                base_url="https://openrouter.ai/api/v1",
                model_id="anthropic/claude-3",
                phase_label="qa",
                openrouter_provider=OpenRouterProviderRoutingConfig(
                    require_parameters=True,
                ),
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is True

    @patch("rentl_llm.provider_factory.detect_provider")
    def test_multiple_endpoints_mixed_results(self, mock_detect: MagicMock) -> None:
        """Mixed compatible/incompatible endpoints report all issues."""

        def side_effect(base_url: str) -> ProviderCapabilities:
            if "openai.com" in base_url:
                return ProviderCapabilities(
                    name="OpenAI",
                    is_openrouter=False,
                    supports_tool_calling=True,
                    supports_tool_choice_required=True,
                )
            return ProviderCapabilities(
                name="BadProvider",
                is_openrouter=False,
                supports_tool_calling=False,
                supports_tool_choice_required=False,
            )

        mock_detect.side_effect = side_effect
        endpoints = [
            PreflightEndpoint(
                base_url="https://api.openai.com/v1",
                model_id="gpt-4o",
                phase_label="translate",
            ),
            PreflightEndpoint(
                base_url="https://bad-provider.com/v1",
                model_id="bad-model",
                phase_label="qa",
            ),
        ]
        result = run_preflight_checks(endpoints)
        assert result.passed is False
        assert len(result.issues) == 2
        assert all(i.phase_label == "qa" for i in result.issues)
        assert mock_detect.call_count == 2

    def test_empty_endpoints_passes(self) -> None:
        """Empty endpoint list passes preflight (no LLM phases)."""
        result = run_preflight_checks([])
        assert result.passed is True
        assert result.issues == []


class TestAssertPreflight:
    """Tests for assert_preflight raising on failure."""

    def test_assert_passes_on_compatible(self) -> None:
        """assert_preflight does not raise for compatible endpoints."""
        endpoints = [
            PreflightEndpoint(
                base_url="https://api.openai.com/v1",
                model_id="gpt-4o",
                phase_label="translate",
            ),
        ]
        assert_preflight(endpoints)

    @patch("rentl_llm.provider_factory.detect_provider")
    def test_assert_raises_on_incompatible(self, mock_detect: MagicMock) -> None:
        """assert_preflight raises ProviderFactoryError on failure."""
        mock_detect.return_value = ProviderCapabilities(
            name="BadProvider",
            is_openrouter=False,
            supports_tool_calling=False,
            supports_tool_choice_required=False,
        )
        endpoints = [
            PreflightEndpoint(
                base_url="https://bad.com/v1",
                model_id="bad-model",
                phase_label="translate",
            ),
        ]
        with pytest.raises(
            ProviderFactoryError, match="Preflight compatibility check failed"
        ):
            assert_preflight(endpoints)
        mock_detect.assert_called_once()

    @patch("rentl_llm.provider_factory.detect_provider")
    def test_assert_error_message_includes_details(
        self, mock_detect: MagicMock
    ) -> None:
        """Error message includes phase, provider, and model details."""
        mock_detect.return_value = ProviderCapabilities(
            name="TestProvider",
            is_openrouter=False,
            supports_tool_calling=True,
            supports_tool_choice_required=False,
        )
        endpoints = [
            PreflightEndpoint(
                base_url="https://test.com/v1",
                model_id="test-model",
                phase_label="qa",
            ),
        ]
        with pytest.raises(
            ProviderFactoryError, match=r".*\[qa\] TestProvider / test-model.*"
        ):
            assert_preflight(endpoints)
        mock_detect.assert_called_once()
