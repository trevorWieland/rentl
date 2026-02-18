"""Integration test: local model factory → OpenAIChatModel → Agent pipeline.

Exercises the full path from create_model() with a local URL through
OpenAIChatModel to a pydantic-ai Agent.run() call, using respx to mock
the HTTP endpoint. Proves the factory correctly routes local URLs to
the generic OpenAI provider and produces a working agent without
requiring a live server.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import respx
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel

from rentl_llm.openai_runtime import OpenAICompatibleRuntime
from rentl_llm.provider_factory import create_model
from rentl_schemas.config import RetryConfig
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmRuntimeSettings,
)
from rentl_schemas.primitives import JsonValue

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

    Args:
        content: The assistant message content.
        model: Model ID to include in the response.

    Returns:
        Dict matching the OpenAI chat completion response schema.
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

    Args:
        tool_name: Name of the function to call.
        arguments: JSON-serializable arguments dict.
        model: Model ID to include in the response.

    Returns:
        Dict matching the OpenAI chat completion response schema with tool_calls.
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

    Args:
        model_id: Model identifier.
        base_url: Local endpoint URL.

    Returns:
        Configured prompt request for local model testing.
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


class TestLocalModelFactoryPipeline:
    """Integration tests for the local model factory-to-agent pipeline."""

    def test_factory_routes_local_url_to_openai_model(self) -> None:
        """create_model with localhost URL produces OpenAIChatModel."""
        with respx.mock:
            # No HTTP call needed — just checking model type
            respx.post(f"{_LOCAL_BASE_URL}/chat/completions").mock(
                return_value=httpx.Response(200, json=_chat_completion_response("ok"))
            )

            model, settings = create_model(
                base_url=_LOCAL_BASE_URL,
                api_key=_LOCAL_API_KEY,
                model_id=_LOCAL_MODEL_ID,
                temperature=0.5,
            )

        assert isinstance(model, OpenAIChatModel)
        assert settings["temperature"] == 0.5

    def test_factory_to_agent_plain_text(self) -> None:
        """Full pipeline: create_model → OpenAIChatModel → Agent.run() → text output."""
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
            result = asyncio.run(agent.run("Say hello", model_settings=settings))

        assert result.output == "Hello from local model!"
        assert route.called

    def test_factory_to_agent_structured_output(self) -> None:
        """Full pipeline with structured output via tool calling."""
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
            result = asyncio.run(agent.run("Say hello", model_settings=settings))

        assert isinstance(result.output, _Greeting)
        assert result.output.message == "Hello from structured output!"
        assert route.called

    def test_runtime_with_local_model(self) -> None:
        """OpenAICompatibleRuntime uses factory correctly for local endpoints."""
        with respx.mock:
            route = respx.post(f"{_LOCAL_BASE_URL}/chat/completions").mock(
                return_value=httpx.Response(
                    200, json=_chat_completion_response("Runtime response")
                )
            )

            runtime = OpenAICompatibleRuntime()
            request = _make_local_request()
            response = asyncio.run(runtime.run_prompt(request, api_key=_LOCAL_API_KEY))

        assert response.output_text == "Runtime response"
        assert response.model_id == _LOCAL_MODEL_ID
        assert route.called
