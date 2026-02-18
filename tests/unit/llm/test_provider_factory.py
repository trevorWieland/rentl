"""Unit tests for LLM provider factory."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.models.openrouter import OpenRouterModelSettings

from rentl_llm.provider_factory import (
    ProviderFactoryError,
    create_model,
    enforce_provider_allowlist,
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
