"""Integration tests for OpenRouter provider parity."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings

from rentl_llm.openai_runtime import OpenAICompatibleRuntime
from rentl_schemas.config import RetryConfig
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmRuntimeSettings,
)


def _make_request(
    *,
    provider_name: str,
    base_url: str,
    model_id: str = "gpt-4",
) -> LlmPromptRequest:
    """Build an LlmPromptRequest with the given endpoint settings.

    Returns:
        Configured prompt request for testing.
    """
    return LlmPromptRequest(
        prompt="Test prompt",
        system_prompt=None,
        runtime=LlmRuntimeSettings(
            endpoint=LlmEndpointTarget(
                provider_name=provider_name,
                base_url=base_url,
                api_key_env="TEST_KEY",
                timeout_s=30.0,
            ),
            model=LlmModelSettings(
                model_id=model_id,
                temperature=0.7,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                max_output_tokens=4096,
                reasoning_effort=None,
            ),
            retry=RetryConfig(max_retries=1, backoff_s=1.0, max_backoff_s=5.0),
        ),
    )


class TestOpenRouterProviderSelection:
    """Tests for OpenRouter provider selection in BYOK runtime."""

    def test_openrouter_base_url_selects_openrouter_provider(self) -> None:
        """OpenRouter base_url should select OpenRouterProvider and OpenRouterModel."""
        runtime = OpenAICompatibleRuntime()

        request = _make_request(
            provider_name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            model_id="anthropic/claude-4.5-sonnet",
        )

        mock_model = MagicMock(spec=OpenRouterModel)
        mock_settings: OpenRouterModelSettings = {
            "temperature": 0.7,
            "openrouter_provider": {"require_parameters": True},
        }

        with (
            patch(
                "rentl_llm.openai_runtime.create_model",
                return_value=(mock_model, mock_settings),
            ) as mock_factory,
            patch("rentl_llm.openai_runtime.Agent") as mock_agent,
        ):
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock()
            mock_agent.return_value = mock_agent_instance

            asyncio.run(runtime.run_prompt(request, api_key="test-key"))

        # Verify factory was called with OpenRouter base_url and api_key
        mock_factory.assert_called_once()
        call_kwargs = mock_factory.call_args.kwargs
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["model_id"] == "anthropic/claude-4.5-sonnet"

        # Verify model returned by factory was passed to Agent
        mock_agent.assert_called_once()
        assert mock_agent.call_args.args[0] is mock_model

        # Verify model_settings from factory were passed to agent.run
        run_kwargs = mock_agent_instance.run.call_args.kwargs
        assert run_kwargs["model_settings"] is mock_settings

    def test_non_openrouter_uses_openai_provider(self) -> None:
        """Non-OpenRouter base_url should use OpenAI provider path in factory."""
        runtime = OpenAICompatibleRuntime()

        request = _make_request(
            provider_name="local",
            base_url="http://localhost:8000/v1",
        )

        mock_model = MagicMock()
        mock_settings: OpenAIChatModelSettings = {"temperature": 0.7}

        with (
            patch(
                "rentl_llm.openai_runtime.create_model",
                return_value=(mock_model, mock_settings),
            ) as mock_factory,
            patch("rentl_llm.openai_runtime.Agent") as mock_agent,
        ):
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock()
            mock_agent.return_value = mock_agent_instance

            asyncio.run(runtime.run_prompt(request, api_key="test-key"))

        # Verify factory was called with non-OpenRouter base_url
        mock_factory.assert_called_once()
        call_kwargs = mock_factory.call_args.kwargs
        assert call_kwargs["base_url"] == "http://localhost:8000/v1"
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["model_id"] == "gpt-4"


class TestProviderSwitching:
    """Tests for provider switching via config."""

    def test_provider_switching_requires_config_only(self) -> None:
        """Switching providers should only require config changes."""
        endpoints = [
            ("openrouter", "https://openrouter.ai/api/v1"),
            ("openai", "https://api.openai.com/v1"),
            ("local", "http://localhost:8000/v1"),
        ]

        for provider_name, base_url in endpoints:
            request = _make_request(
                provider_name=provider_name,
                base_url=base_url,
            )

            runtime = OpenAICompatibleRuntime()

            mock_model = MagicMock()
            mock_settings: OpenAIChatModelSettings = {"temperature": 0.7}

            with (
                patch(
                    "rentl_llm.openai_runtime.create_model",
                    return_value=(mock_model, mock_settings),
                ) as mock_factory,
                patch("rentl_llm.openai_runtime.Agent") as mock_agent,
            ):
                mock_agent_instance = MagicMock()
                mock_agent_instance.run = AsyncMock()
                mock_agent.return_value = mock_agent_instance

                asyncio.run(runtime.run_prompt(request, api_key="test-key"))

                # Verify factory was called with the correct base_url
                mock_factory.assert_called_once()
                assert mock_factory.call_args.kwargs["base_url"] == base_url
