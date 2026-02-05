"""Integration tests for OpenRouter provider parity."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.providers.openrouter import OpenRouterProvider

from rentl_llm.openai_runtime import OpenAICompatibleRuntime
from rentl_schemas.config import RetryConfig
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmRuntimeSettings,
)


class TestOpenRouterProviderSelection:
    """Tests for OpenRouter provider selection in BYOK runtime."""

    def test_openrouter_base_url_selects_openrouter_provider(self) -> None:
        """OpenRouter base_url should select OpenRouterProvider and OpenRouterModel."""
        runtime = OpenAICompatibleRuntime()

        request = LlmPromptRequest(
            prompt="Test prompt",
            system_prompt=None,
            runtime=LlmRuntimeSettings(
                endpoint=LlmEndpointTarget(
                    provider_name="openrouter",
                    base_url="https://openrouter.ai/api/v1",
                    api_key_env="TEST_KEY",
                    timeout_s=30.0,
                ),
                model=LlmModelSettings(
                    model_id="anthropic/claude-3.5-sonnet",
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

        with (
            patch("rentl_llm.openai_runtime.OpenRouterProvider") as mock_provider,
            patch("rentl_llm.openai_runtime.OpenRouterModel") as mock_model,
            patch("rentl_llm.openai_runtime.Agent") as mock_agent,
        ):
            mock_provider.return_value = MagicMock()
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock()
            mock_agent.return_value = mock_agent_instance

            # Run should trigger provider selection
            asyncio.run(runtime.run_prompt(request, api_key="test-key"))

        # Verify OpenRouterProvider was instantiated
        assert mock_provider.called
        assert mock_model.called
        call_kwargs = mock_provider.call_args.kwargs
        assert call_kwargs["api_key"] == "test-key"
        model_settings = mock_agent_instance.run.call_args.kwargs["model_settings"]
        assert model_settings["openrouter_provider"]["require_parameters"] is True

    def test_non_openrouter_uses_openai_provider(self) -> None:
        """Non-OpenRouter base_url should use OpenAIProvider."""
        runtime = OpenAICompatibleRuntime()

        request = LlmPromptRequest(
            prompt="Test prompt",
            system_prompt=None,
            runtime=LlmRuntimeSettings(
                endpoint=LlmEndpointTarget(
                    provider_name="local",
                    base_url="http://localhost:8000/v1",
                    api_key_env="TEST_KEY",
                    timeout_s=30.0,
                ),
                model=LlmModelSettings(
                    model_id="gpt-4",
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

        with (
            patch("rentl_llm.openai_runtime.OpenAIProvider") as mock_provider,
            patch("rentl_llm.openai_runtime.OpenRouterProvider") as mock_openrouter,
            patch("rentl_llm.openai_runtime.OpenAIChatModel"),
            patch("rentl_llm.openai_runtime.OpenRouterModel") as mock_openrouter_model,
            patch("rentl_llm.openai_runtime.Agent") as mock_agent,
        ):
            mock_provider.return_value = MagicMock()
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock()
            mock_agent.return_value = mock_agent_instance

            asyncio.run(runtime.run_prompt(request, api_key="test-key"))

        # Verify OpenAIProvider was called, not OpenRouterProvider
        assert mock_provider.called
        assert not mock_openrouter.called
        assert not mock_openrouter_model.called


class TestProviderSwitching:
    """Tests for provider switching via config."""

    def test_provider_switching_requires_config_only(self) -> None:
        """Switching providers should only require config changes."""
        # This test validates that the runtime adapts based on base_url
        # without requiring code changes

        endpoints = [
            ("openrouter", "https://openrouter.ai/api/v1", OpenRouterProvider),
            ("openai", "https://api.openai.com/v1", "OpenAIProvider"),
            ("local", "http://localhost:8000/v1", "OpenAIProvider"),
        ]

        for provider_name, base_url, expected_provider in endpoints:
            request = LlmPromptRequest(
                prompt="Test",
                system_prompt=None,
                runtime=LlmRuntimeSettings(
                    endpoint=LlmEndpointTarget(
                        provider_name=provider_name,
                        base_url=base_url,
                        api_key_env="TEST_KEY",
                        timeout_s=30.0,
                    ),
                    model=LlmModelSettings(
                        model_id="gpt-4",
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

            runtime = OpenAICompatibleRuntime()

            with (
                patch("rentl_llm.openai_runtime.OpenRouterProvider") as mock_or,
                patch("rentl_llm.openai_runtime.OpenAIProvider") as mock_oai,
                patch("rentl_llm.openai_runtime.OpenAIChatModel"),
                patch("rentl_llm.openai_runtime.OpenRouterModel") as mock_or_model,
                patch("rentl_llm.openai_runtime.Agent") as mock_agent,
            ):
                mock_or.return_value = MagicMock()
                mock_oai.return_value = MagicMock()
                mock_agent_instance = MagicMock()
                mock_agent_instance.run = AsyncMock()
                mock_agent.return_value = mock_agent_instance

                asyncio.run(runtime.run_prompt(request, api_key="test-key"))

                # Verify correct provider was selected based on base_url
                if expected_provider == OpenRouterProvider:
                    assert mock_or.called, f"Expected OpenRouterProvider for {base_url}"
                    assert mock_or_model.called, (
                        f"Expected OpenRouterModel for {base_url}"
                    )
                else:
                    assert mock_oai.called, f"Expected OpenAIProvider for {base_url}"
                    assert not mock_or_model.called
