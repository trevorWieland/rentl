"""BDD integration tests for OpenRouter provider parity.

Verifies that OpenAICompatibleRuntime correctly routes requests through
the provider factory based on base_url, using HTTP-level mocking (respx)
to avoid patching internal pydantic-ai classes.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
import respx
from pytest_bdd import given, scenarios, then, when

from rentl_llm.openai_runtime import OpenAICompatibleRuntime
from rentl_schemas.config import RetryConfig
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmPromptResponse,
    LlmRuntimeSettings,
)

pytestmark = pytest.mark.integration

# Link feature file
scenarios("../features/byok/openrouter_runtime.feature")


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


class OpenRouterContext:
    """Context object for OpenRouter BDD scenarios."""

    runtime: OpenAICompatibleRuntime | None = None
    request: LlmPromptRequest | None = None
    response: LlmPromptResponse | None = None
    route: Any = None
    # For multi-endpoint scenario
    endpoints: list[tuple[str, str, str]] | None = None
    results: list[tuple[Any, LlmPromptResponse]] | None = None


@given("an OpenRouter endpoint configuration", target_fixture="ctx")
def given_openrouter_config() -> OpenRouterContext:
    """Set up an OpenRouter endpoint configuration with runtime and request.

    Returns:
        OpenRouterContext with fields initialized.
    """
    ctx = OpenRouterContext()
    ctx.runtime = OpenAICompatibleRuntime()
    ctx.request = _make_request(
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model_id="anthropic/claude-4.5-sonnet",
    )
    return ctx


@given("a local endpoint configuration", target_fixture="ctx")
def given_local_config() -> OpenRouterContext:
    """Set up a local endpoint configuration with runtime and request.

    Returns:
        OpenRouterContext with fields initialized.
    """
    ctx = OpenRouterContext()
    ctx.runtime = OpenAICompatibleRuntime()
    ctx.request = _make_request(
        provider_name="local",
        base_url="http://localhost:8000/v1",
    )
    return ctx


@given("multiple endpoint configurations for different providers", target_fixture="ctx")
def given_multiple_endpoints() -> OpenRouterContext:
    """Set up multiple endpoint configurations for provider parity testing.

    Returns:
        OpenRouterContext with fields initialized.
    """
    ctx = OpenRouterContext()
    ctx.endpoints = [
        ("openrouter", "https://openrouter.ai/api/v1", "openai/gpt-4"),
        ("openai", "https://api.openai.com/v1", "gpt-4"),
        ("local", "http://localhost:8000/v1", "gpt-4"),
    ]
    ctx.results = []
    return ctx


@when("I send a prompt through the runtime")
def when_send_prompt(ctx: OpenRouterContext) -> None:
    """Send a prompt through the runtime with mocked HTTP endpoint."""
    assert ctx.runtime is not None
    assert ctx.request is not None

    base_url = ctx.request.runtime.endpoint.base_url
    model_id = ctx.request.runtime.model.model_id
    is_openrouter = "openrouter" in base_url

    with respx.mock:
        route = respx.post(f"{base_url}/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_chat_completion_response(
                    "Test response",
                    model_id,
                    openrouter=is_openrouter,
                ),
            )
        )
        ctx.response = asyncio.run(
            ctx.runtime.run_prompt(ctx.request, api_key="test-key")
        )
        ctx.route = route


@when("I send prompts through each endpoint")
def when_send_prompts_through_each(ctx: OpenRouterContext) -> None:
    """Send prompts through each configured endpoint with mocked HTTP."""
    assert ctx.endpoints is not None
    assert ctx.results is not None

    for provider_name, base_url, model_id in ctx.endpoints:
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
            ctx.results.append((route, response))


@then("the request is sent to the OpenRouter endpoint")
def then_request_sent_to_openrouter(ctx: OpenRouterContext) -> None:
    """Assert the request was routed to the OpenRouter endpoint."""
    assert ctx.route is not None
    assert ctx.route.called


@then("the request is sent to the local endpoint")
def then_request_sent_to_local(ctx: OpenRouterContext) -> None:
    """Assert the request was routed to the local endpoint."""
    assert ctx.route is not None
    assert ctx.route.called


@then("the response contains the expected output")
def then_response_contains_output(ctx: OpenRouterContext) -> None:
    """Assert the response contains the expected output text."""
    assert ctx.response is not None
    assert ctx.response.output_text == "Test response"


@then("each request reaches the correct endpoint")
def then_each_request_reaches_endpoint(ctx: OpenRouterContext) -> None:
    """Assert each request was routed to its respective endpoint."""
    assert ctx.results is not None
    for route, _response in ctx.results:
        assert route.called


@then("each response contains the correct model ID")
def then_each_response_correct_model(ctx: OpenRouterContext) -> None:
    """Assert each response contains the model ID matching its endpoint config."""
    assert ctx.results is not None
    assert ctx.endpoints is not None
    for i, (_route, response) in enumerate(ctx.results):
        _provider_name, _base_url, model_id = ctx.endpoints[i]
        assert response.model_id == model_id
