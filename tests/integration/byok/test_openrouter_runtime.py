"""Integration tests for OpenRouter provider parity.

Verifies that OpenAICompatibleRuntime correctly routes requests through
the provider factory based on base_url, using HTTP-level mocking (respx)
to avoid patching internal pydantic-ai classes.
"""

from __future__ import annotations

import asyncio

import httpx
import respx

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


def _chat_completion_response(
    content: str, model: str = "gpt-4", *, openrouter: bool = False
) -> dict[str, object]:
    """Build a minimal OpenAI-compatible chat completion response.

    Args:
        content: The assistant message content.
        model: Model ID to include in the response.
        openrouter: If True, include OpenRouter-specific fields
            (native_finish_reason, provider).

    Returns:
        Dict matching the OpenAI chat completion response schema.
    """
    choice: dict[str, object] = {
        "index": 0,
        "message": {"role": "assistant", "content": content},
        "finish_reason": "stop",
    }
    if openrouter:
        choice["native_finish_reason"] = "stop"

    response: dict[str, object] = {
        "id": "chatcmpl-mock-openrouter",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [choice],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    if openrouter:
        response["provider"] = "OpenAI"

    return response


class TestOpenRouterProviderSelection:
    """Tests for OpenRouter provider selection in BYOK runtime."""

    def test_openrouter_base_url_selects_openrouter_provider(self) -> None:
        """OpenRouter base_url should route through OpenRouter provider."""
        runtime = OpenAICompatibleRuntime()

        request = _make_request(
            provider_name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            model_id="anthropic/claude-4.5-sonnet",
        )

        with respx.mock:
            route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json=_chat_completion_response(
                        "OpenRouter response",
                        "anthropic/claude-4.5-sonnet",
                        openrouter=True,
                    ),
                )
            )

            response = asyncio.run(runtime.run_prompt(request, api_key="test-key"))

        # Verify the HTTP request was sent to OpenRouter
        assert route.called
        assert response.output_text == "OpenRouter response"
        assert response.model_id == "anthropic/claude-4.5-sonnet"

    def test_non_openrouter_uses_openai_provider(self) -> None:
        """Non-OpenRouter base_url should route through OpenAI provider."""
        runtime = OpenAICompatibleRuntime()

        request = _make_request(
            provider_name="local",
            base_url="http://localhost:8000/v1",
        )

        with respx.mock:
            route = respx.post("http://localhost:8000/v1/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json=_chat_completion_response("Local response"),
                )
            )

            response = asyncio.run(runtime.run_prompt(request, api_key="test-key"))

        # Verify the HTTP request was sent to the local endpoint
        assert route.called
        assert response.output_text == "Local response"
        assert response.model_id == "gpt-4"


class TestProviderSwitching:
    """Tests for provider switching via config."""

    def test_provider_switching_requires_config_only(self) -> None:
        """Switching providers should only require config changes."""
        endpoints = [
            ("openrouter", "https://openrouter.ai/api/v1", "openai/gpt-4"),
            ("openai", "https://api.openai.com/v1", "gpt-4"),
            ("local", "http://localhost:8000/v1", "gpt-4"),
        ]

        for provider_name, base_url, model_id in endpoints:
            request = _make_request(
                provider_name=provider_name,
                base_url=base_url,
                model_id=model_id,
            )

            runtime = OpenAICompatibleRuntime()
            is_openrouter = "openrouter" in base_url

            with respx.mock:
                route = respx.post(f"{base_url}/chat/completions").mock(
                    return_value=httpx.Response(
                        200,
                        json=_chat_completion_response(
                            "Response", model_id, openrouter=is_openrouter
                        ),
                    )
                )

                response = asyncio.run(runtime.run_prompt(request, api_key="test-key"))

                # Verify the correct endpoint was called
                assert route.called
                assert response.model_id == model_id
