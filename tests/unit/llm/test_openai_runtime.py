"""Tests for OpenAI-compatible runtime adapter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from pydantic import Field
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from rentl_llm.openai_runtime import OpenAICompatibleRuntime
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import OpenRouterProviderRoutingConfig, RetryConfig
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmRuntimeSettings,
)
from rentl_schemas.primitives import ReasoningEffort

if TYPE_CHECKING:
    from collections.abc import Generator


class TestOutput(BaseSchema):
    """Test output schema for structured output tests."""

    winner: str = Field(..., description="Winner")
    score: int = Field(..., description="Score")


@pytest.fixture
def function_model() -> FunctionModel:
    """FunctionModel that returns plain text through real pydantic-ai Agent.

    Returns:
        FunctionModel: Deterministic model for testing.
    """
    return FunctionModel(
        lambda msgs, info: ModelResponse(parts=[TextPart(content="Test response")])
    )


@pytest.fixture
def mock_create_model(function_model: FunctionModel) -> Generator[MagicMock]:
    """Mock create_model to return FunctionModel instead of hitting real endpoints.

    Yields:
        MagicMock: Mocked create_model function.
    """
    with patch(
        "rentl_llm.openai_runtime.create_model",
        return_value=(function_model, {"temperature": 0.7, "timeout": 30.0}),
    ) as mock:
        yield mock


@pytest.fixture
def runtime() -> OpenAICompatibleRuntime:
    """Create runtime instance.

    Returns:
        OpenAICompatibleRuntime: Runtime adapter instance.
    """
    return OpenAICompatibleRuntime()


def _build_request(
    base_url: str = "https://api.openai.com/v1",
    model_id: str = "gpt-4",
    reasoning_effort: ReasoningEffort | None = None,
    max_output_tokens: int | None = None,
    openrouter_provider: OpenRouterProviderRoutingConfig | None = None,
) -> LlmPromptRequest:
    """Build test request.

    Args:
        base_url: Endpoint base URL.
        model_id: Model identifier.
        reasoning_effort: Reasoning effort level.
        max_output_tokens: Max output tokens.
        openrouter_provider: OpenRouter provider config.

    Returns:
        LlmPromptRequest: Test request payload.
    """
    return LlmPromptRequest(
        runtime=LlmRuntimeSettings(
            endpoint=LlmEndpointTarget(
                provider_name="openai",
                base_url=base_url,
                api_key_env="OPENAI_API_KEY",
                timeout_s=30.0,
                openrouter_provider=openrouter_provider,
            ),
            model=LlmModelSettings(
                model_id=model_id,
                temperature=0.7,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
            ),
            retry=RetryConfig(),
        ),
        system_prompt="Test system prompt",
        prompt="Test prompt",
    )


@pytest.mark.asyncio
async def test_run_prompt_openai(
    runtime: OpenAICompatibleRuntime,
    mock_create_model: MagicMock,
) -> None:
    """Test running prompt with OpenAI provider.

    Args:
        runtime: Runtime instance.
        mock_create_model: Mocked create_model factory.
    """
    request = _build_request()
    response = await runtime.run_prompt(request, api_key="test-key")
    assert response.model_id == "gpt-4"
    assert response.output_text == "Test response"
    mock_create_model.assert_called_once()


@pytest.mark.asyncio
async def test_run_prompt_openrouter(
    runtime: OpenAICompatibleRuntime,
    mock_create_model: MagicMock,
) -> None:
    """Test running prompt with OpenRouter provider.

    Args:
        runtime: Runtime instance.
        mock_create_model: Mocked create_model factory.
    """
    request = _build_request(base_url="https://openrouter.ai/api/v1")
    response = await runtime.run_prompt(request, api_key="test-key")
    assert response.model_id == "gpt-4"
    assert response.output_text == "Test response"
    mock_create_model.assert_called_once()
    assert (
        mock_create_model.call_args.kwargs["base_url"] == "https://openrouter.ai/api/v1"
    )


@pytest.mark.asyncio
async def test_run_prompt_with_reasoning_effort(
    runtime: OpenAICompatibleRuntime,
    mock_create_model: MagicMock,
) -> None:
    """Test reasoning effort parameter.

    Args:
        runtime: Runtime instance.
        mock_create_model: Mocked create_model factory.
    """
    request = _build_request(reasoning_effort=ReasoningEffort.MEDIUM)
    response = await runtime.run_prompt(request, api_key="test-key")
    assert response.model_id == "gpt-4"
    mock_create_model.assert_called_once()
    assert (
        mock_create_model.call_args.kwargs["reasoning_effort"] == ReasoningEffort.MEDIUM
    )


@pytest.mark.asyncio
async def test_run_prompt_without_system_prompt(
    runtime: OpenAICompatibleRuntime,
    mock_create_model: MagicMock,
) -> None:
    """Test prompt without system instructions.

    Args:
        runtime: Runtime instance.
        mock_create_model: Mocked create_model factory.
    """
    request = _build_request()
    request.system_prompt = None
    response = await runtime.run_prompt(request, api_key="test-key")
    assert response.model_id == "gpt-4"
    mock_create_model.assert_called_once()


@pytest.mark.asyncio
async def test_run_prompt_default_max_tokens(
    runtime: OpenAICompatibleRuntime,
    mock_create_model: MagicMock,
) -> None:
    """Test default max output tokens.

    Args:
        runtime: Runtime instance.
        mock_create_model: Mocked create_model factory.
    """
    request = _build_request(max_output_tokens=None)
    response = await runtime.run_prompt(request, api_key="test-key")
    assert response.model_id == "gpt-4"
    mock_create_model.assert_called_once()
    assert mock_create_model.call_args.kwargs["max_output_tokens"] == 4096


@pytest.mark.asyncio
async def test_run_prompt_custom_max_tokens(
    runtime: OpenAICompatibleRuntime,
    mock_create_model: MagicMock,
) -> None:
    """Test custom max output tokens.

    Args:
        runtime: Runtime instance.
        mock_create_model: Mocked create_model factory.
    """
    request = _build_request(max_output_tokens=8192)
    response = await runtime.run_prompt(request, api_key="test-key")
    assert response.model_id == "gpt-4"
    mock_create_model.assert_called_once()
    assert mock_create_model.call_args.kwargs["max_output_tokens"] == 8192


@pytest.mark.asyncio
async def test_run_prompt_openrouter_with_reasoning(
    runtime: OpenAICompatibleRuntime,
    mock_create_model: MagicMock,
) -> None:
    """Test OpenRouter with reasoning effort.

    Args:
        runtime: Runtime instance.
        mock_create_model: Mocked create_model factory.
    """
    request = _build_request(
        base_url="https://openrouter.ai/api/v1",
        reasoning_effort=ReasoningEffort.HIGH,
    )
    response = await runtime.run_prompt(request, api_key="test-key")
    assert response.model_id == "gpt-4"
    mock_create_model.assert_called_once()
    assert (
        mock_create_model.call_args.kwargs["reasoning_effort"] == ReasoningEffort.HIGH
    )


@pytest.mark.asyncio
async def test_run_prompt_with_structured_output(
    runtime: OpenAICompatibleRuntime,
) -> None:
    """Test structured output with result_schema.

    Args:
        runtime: Runtime instance.
    """
    structured_model = FunctionModel(
        lambda msgs, info: ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="final_result",
                    args=json.dumps({"winner": "A", "score": 10}),
                )
            ]
        )
    )
    with patch(
        "rentl_llm.openai_runtime.create_model",
        return_value=(structured_model, {"temperature": 0.7, "timeout": 30.0}),
    ) as mock_create_model:
        request = _build_request()
        request.result_schema = TestOutput

        response = await runtime.run_prompt(request, api_key="test-key")

        assert response.model_id == "gpt-4"
        assert response.structured_output is not None
        assert isinstance(response.structured_output, TestOutput)
        assert response.structured_output.winner == "A"
        assert response.structured_output.score == 10
        mock_create_model.assert_called_once()
