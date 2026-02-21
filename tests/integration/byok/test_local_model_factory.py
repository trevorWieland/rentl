"""BDD integration tests for local model factory to agent pipeline.

Exercises the full path from create_model() with a local URL through
OpenAIChatModel to a pydantic-ai Agent.run() call, using respx to mock
the HTTP endpoint. Proves the factory correctly routes local URLs to
the generic OpenAI provider and produces a working agent without
requiring a live server.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest
import respx
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pytest_bdd import given, scenarios, then, when

from rentl_llm.openai_runtime import OpenAICompatibleRuntime
from rentl_llm.provider_factory import create_model
from rentl_schemas.config import RetryConfig
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmPromptResponse,
    LlmRuntimeSettings,
)
from rentl_schemas.primitives import JsonValue

pytestmark = pytest.mark.integration

# Link feature file
scenarios("../features/byok/local_model_factory.feature")

_LOCAL_BASE_URL = "http://localhost:5000/v1"
_LOCAL_MODEL_ID = "openai/gpt-oss-20b"
_LOCAL_API_KEY = "test-local-key"


class _Greeting(BaseModel):
    """Structured output schema for testing."""

    message: str = Field(..., description="The greeting message")


def _chat_completion_response(
    content: str, model: str = _LOCAL_MODEL_ID
) -> dict[str, JsonValue]:
    """Build a minimal OpenAI-compatible chat completion response.

    Returns:
        Dict representing an OpenAI chat completion response.
    """
    return {
        "id": "chatcmpl-mock-local",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


def _tool_call_response(
    tool_name: str,
    arguments: dict[str, JsonValue],
    model: str = _LOCAL_MODEL_ID,
) -> dict[str, JsonValue]:
    """Build a chat completion response with a tool call (structured output).

    Returns:
        Dict representing an OpenAI chat completion response with tool calls.
    """
    return {
        "id": "chatcmpl-mock-tool",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_1",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 10,
            "total_tokens": 25,
        },
    }


def _make_local_request(
    model_id: str = _LOCAL_MODEL_ID,
    base_url: str = _LOCAL_BASE_URL,
) -> LlmPromptRequest:
    """Build an LlmPromptRequest targeting a local endpoint.

    Returns:
        LlmPromptRequest configured for a local endpoint.
    """
    return LlmPromptRequest(
        prompt="Say hello",
        system_prompt="You are a test assistant.",
        runtime=LlmRuntimeSettings(
            endpoint=LlmEndpointTarget(
                provider_name="local",
                base_url=base_url,
                api_key_env="TEST_LOCAL_KEY",
                timeout_s=30.0,
            ),
            model=LlmModelSettings(
                model_id=model_id,
                temperature=0.5,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                max_output_tokens=4096,
                reasoning_effort=None,
            ),
            retry=RetryConfig(max_retries=1, backoff_s=1.0, max_backoff_s=5.0),
        ),
    )


class LocalModelContext:
    """Context object for local model factory BDD scenarios."""

    model: Any = None
    settings: Any = None
    agent_result: Any = None
    runtime_response: LlmPromptResponse | None = None
    route_called: bool = False


@given("a local model endpoint", target_fixture="ctx")
def given_local_endpoint() -> LocalModelContext:
    """Set up a local model endpoint context.

    Returns:
        LocalModelContext with fields initialized.
    """
    return LocalModelContext()


@given("a local model endpoint with mocked HTTP", target_fixture="ctx")
def given_local_endpoint_mocked_http() -> LocalModelContext:
    """Set up a local model endpoint with HTTP mocking enabled.

    Returns:
        LocalModelContext with fields initialized.
    """
    return LocalModelContext()


@given("a local model endpoint with mocked tool call HTTP", target_fixture="ctx")
def given_local_endpoint_mocked_tool() -> LocalModelContext:
    """Set up a local model endpoint with tool call HTTP mocking.

    Returns:
        LocalModelContext with fields initialized.
    """
    return LocalModelContext()


@when("I create a model through the factory")
def when_create_model(ctx: LocalModelContext) -> None:
    """Create a model via the provider factory (no HTTP calls needed)."""
    ctx.model, ctx.settings = create_model(
        base_url=_LOCAL_BASE_URL,
        api_key=_LOCAL_API_KEY,
        model_id=_LOCAL_MODEL_ID,
        temperature=0.5,
    )


@when("I run an agent with plain text output")
def when_run_agent_plain_text(ctx: LocalModelContext) -> None:
    """Run an agent that produces plain text output via mocked HTTP."""
    with respx.mock:
        route = respx.post(f"{_LOCAL_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200, json=_chat_completion_response("Hello from local model!")
            )
        )
        model, settings = create_model(
            base_url=_LOCAL_BASE_URL,
            api_key=_LOCAL_API_KEY,
            model_id=_LOCAL_MODEL_ID,
            temperature=0.5,
        )
        agent = Agent(model, instructions="You are a test assistant.")
        ctx.agent_result = asyncio.run(agent.run("Say hello", model_settings=settings))
        ctx.route_called = route.called


@when("I run an agent with structured output")
def when_run_agent_structured(ctx: LocalModelContext) -> None:
    """Run an agent that produces structured pydantic output via mocked HTTP."""
    with respx.mock:
        route = respx.post(f"{_LOCAL_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_tool_call_response(
                    tool_name="final_result",
                    arguments={"message": "Hello from structured output!"},
                ),
            )
        )
        model, settings = create_model(
            base_url=_LOCAL_BASE_URL,
            api_key=_LOCAL_API_KEY,
            model_id=_LOCAL_MODEL_ID,
            temperature=0.5,
        )
        agent = Agent(model, output_type=_Greeting, instructions="Greet the user.")
        ctx.agent_result = asyncio.run(agent.run("Say hello", model_settings=settings))
        ctx.route_called = route.called


@when("I run a prompt through the OpenAI-compatible runtime")
def when_run_through_runtime(ctx: LocalModelContext) -> None:
    """Run a prompt through the OpenAI-compatible runtime with mocked HTTP."""
    with respx.mock:
        route = respx.post(f"{_LOCAL_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                200, json=_chat_completion_response("Runtime response")
            )
        )
        runtime = OpenAICompatibleRuntime()
        request = _make_local_request()
        ctx.runtime_response = asyncio.run(
            runtime.run_prompt(request, api_key=_LOCAL_API_KEY)
        )
        ctx.route_called = route.called


@then("the model is an OpenAIChatModel instance")
def then_model_is_openai(ctx: LocalModelContext) -> None:
    """Assert the created model is an OpenAIChatModel instance."""
    assert isinstance(ctx.model, OpenAIChatModel)


@then("the temperature setting is preserved")
def then_temperature_preserved(ctx: LocalModelContext) -> None:
    """Assert the temperature model setting is preserved through the factory."""
    assert ctx.settings is not None
    assert ctx.settings["temperature"] == 0.5


@then("the agent returns the mocked text response")
def then_agent_returns_text(ctx: LocalModelContext) -> None:
    """Assert the agent output matches the mocked plain text response."""
    assert ctx.agent_result is not None
    assert ctx.agent_result.output == "Hello from local model!"


@then("the agent returns the structured response")
def then_agent_returns_structured(ctx: LocalModelContext) -> None:
    """Assert the agent output is a valid structured _Greeting instance."""
    assert ctx.agent_result is not None
    assert isinstance(ctx.agent_result.output, _Greeting)
    assert ctx.agent_result.output.message == "Hello from structured output!"


@then("the HTTP endpoint was called")
def then_http_called(ctx: LocalModelContext) -> None:
    """Assert the mocked HTTP endpoint received a request."""
    assert ctx.route_called


@then("the runtime returns the expected response")
def then_runtime_returns_response(ctx: LocalModelContext) -> None:
    """Assert the runtime response contains the expected output text and model ID."""
    assert ctx.runtime_response is not None
    assert ctx.runtime_response.output_text == "Runtime response"
    assert ctx.runtime_response.model_id == _LOCAL_MODEL_ID
