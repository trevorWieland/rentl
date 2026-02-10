"""Integration tests for MTL baseline generation flow."""

import asyncio
from unittest.mock import MagicMock

import pytest

from rentl_core.benchmark.mtl_baseline import MTLBaselineGenerator
from rentl_schemas.config import RetryConfig
from rentl_schemas.io import SourceLine
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmPromptResponse,
    LlmRuntimeSettings,
)


@pytest.fixture
def runtime_settings() -> LlmRuntimeSettings:
    """Create test runtime settings.

    Returns:
        Runtime settings for tests.
    """
    endpoint = LlmEndpointTarget(
        endpoint_ref="test",
        provider_name="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        timeout_s=30.0,
        openrouter_provider=None,
    )
    model = LlmModelSettings(
        model_id="gpt-4o-mini",
        temperature=0.7,
        max_output_tokens=None,
        reasoning_effort=None,
        top_p=1.0,
        presence_penalty=0.0,
        frequency_penalty=0.0,
    )
    retry = RetryConfig(
        max_retries=3,
        backoff_s=1.0,
        max_backoff_s=10.0,
    )
    return LlmRuntimeSettings(endpoint=endpoint, model=model, retry=retry)


@pytest.mark.asyncio
async def test_mtl_baseline_end_to_end_with_mocked_llm(
    runtime_settings: LlmRuntimeSettings,
) -> None:
    """Test complete MTL baseline flow with mocked LLM validates prompt structure."""
    sources = [
        SourceLine(
            scene_id="integration_1",
            line_id="line_1",
            text="こんにちは。",
            speaker="hi",
        ),
        SourceLine(
            scene_id="integration_1",
            line_id="line_2",
            text="さようなら。",
            speaker=None,
        ),
    ]

    # Mock LLM runtime and capture prompts
    captured_prompts = []

    async def mock_run_prompt(  # noqa: RUF029
        request: LlmPromptRequest, api_key: str
    ) -> LlmPromptResponse:
        captured_prompts.append(request.prompt)
        if "こんにちは" in request.prompt:
            return LlmPromptResponse(model_id="gpt-4o-mini", output_text="Hello.")
        else:
            return LlmPromptResponse(model_id="gpt-4o-mini", output_text="Goodbye.")

    mock_runtime = MagicMock()
    mock_runtime.run_prompt = mock_run_prompt

    generator = MTLBaselineGenerator(
        runtime=mock_runtime,
        runtime_settings=runtime_settings,
        api_key="test-key",
        concurrency_limit=5,
    )

    results = await generator.generate_baseline(sources)

    # Verify prompt structure for all calls
    assert len(captured_prompts) == 2
    for prompt in captured_prompts:
        # Minimal prompt structure
        assert "Translate the following Japanese text to English:" in prompt
        # No context injection
        assert "context" not in prompt.lower()
        assert "previous" not in prompt.lower()

    # Verify results
    assert len(results) == 2
    assert results[0].text == "Hello."
    assert results[0].metadata["mtl_baseline"]  # type: ignore[index] is True
    assert results[1].text == "Goodbye."
    assert results[1].metadata["mtl_baseline"]  # type: ignore[index] is True


@pytest.mark.asyncio
async def test_mtl_baseline_concurrency_limit_respected(
    runtime_settings: LlmRuntimeSettings,
) -> None:
    """Test concurrency limit prevents overwhelming LLM endpoint."""
    concurrency_limit = 2

    # Create more sources than concurrency limit
    sources = [
        SourceLine(
            scene_id="test_1",
            line_id=f"line_{i}",
            text=f"テスト{i}",
            speaker=None,
        )
        for i in range(10)
    ]

    # Track concurrent calls
    active_calls = 0
    max_concurrent_calls = 0

    async def mock_run_prompt(
        request: LlmPromptRequest, api_key: str
    ) -> LlmPromptResponse:
        nonlocal active_calls, max_concurrent_calls
        active_calls += 1
        max_concurrent_calls = max(max_concurrent_calls, active_calls)
        # Simulate some async work
        await asyncio.sleep(0.01)
        active_calls -= 1
        return LlmPromptResponse(model_id="gpt-4o-mini", output_text="Translation")

    mock_runtime = MagicMock()
    mock_runtime.run_prompt = mock_run_prompt

    generator = MTLBaselineGenerator(
        runtime=mock_runtime,
        runtime_settings=runtime_settings,
        api_key="test-key",
        concurrency_limit=concurrency_limit,
    )

    await generator.generate_baseline(sources)

    # Verify concurrency was limited
    assert max_concurrent_calls <= concurrency_limit
    # Verify all translations completed
    assert active_calls == 0  # All calls finished
