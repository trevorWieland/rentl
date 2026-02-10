"""BDD integration tests for MTL baseline generation flow."""

import asyncio
from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, scenarios, then, when

from rentl_core.benchmark.mtl_baseline import MTLBaselineGenerator
from rentl_schemas.config import RetryConfig
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmPromptResponse,
    LlmRuntimeSettings,
)

# Link feature file
scenarios("../features/benchmark/mtl_baseline.feature")


class MTLBaselineContext:
    """Context object for MTL baseline BDD scenarios."""

    sources: list[SourceLine] | None = None
    runtime_settings: LlmRuntimeSettings | None = None
    mock_runtime: MagicMock | None = None
    generator: MTLBaselineGenerator | None = None
    results: list[TranslatedLine] | None = None
    captured_prompts: list[str] | None = None
    concurrency_limit: int = 10
    max_concurrent_calls: int = 0


def _create_runtime_settings() -> LlmRuntimeSettings:
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


@given("a set of source lines for translation", target_fixture="ctx")
def given_source_lines() -> MTLBaselineContext:
    """Create a set of source lines for translation.

    Returns:
        MTLBaselineContext with source lines initialized.
    """
    ctx = MTLBaselineContext()
    ctx.sources = [
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
    ctx.runtime_settings = _create_runtime_settings()
    ctx.captured_prompts = []
    return ctx


@given("a large set of source lines", target_fixture="ctx")
def given_large_source_lines() -> MTLBaselineContext:
    """Create a large set of source lines for concurrency testing.

    Returns:
        MTLBaselineContext with many source lines.
    """
    ctx = MTLBaselineContext()
    ctx.sources = [
        SourceLine(
            scene_id="test_1",
            line_id=f"line_{i}",
            text=f"テスト{i}",
            speaker=None,
        )
        for i in range(10)
    ]
    ctx.runtime_settings = _create_runtime_settings()
    return ctx


@given("a mocked LLM runtime")
def given_mocked_runtime(ctx: MTLBaselineContext) -> None:
    """Create a mocked LLM runtime that captures prompts.

    Args:
        ctx: Context with captured_prompts list.
    """
    assert ctx.captured_prompts is not None

    async def mock_run_prompt(  # noqa: RUF029
        request: LlmPromptRequest, api_key: str
    ) -> LlmPromptResponse:
        ctx.captured_prompts.append(request.prompt)  # type: ignore[union-attr]
        if "こんにちは" in request.prompt:
            return LlmPromptResponse(model_id="gpt-4o-mini", output_text="Hello.")
        else:
            return LlmPromptResponse(model_id="gpt-4o-mini", output_text="Goodbye.")

    ctx.mock_runtime = MagicMock()
    ctx.mock_runtime.run_prompt = mock_run_prompt  # type: ignore[assignment]


@given("a mocked LLM runtime that tracks concurrency")
def given_mocked_runtime_with_tracking(ctx: MTLBaselineContext) -> None:
    """Create a mocked LLM runtime that tracks concurrent calls.

    Args:
        ctx: Context to store concurrency tracking.
    """
    active_calls = 0

    async def mock_run_prompt(
        request: LlmPromptRequest, api_key: str
    ) -> LlmPromptResponse:
        nonlocal active_calls
        active_calls += 1
        ctx.max_concurrent_calls = max(ctx.max_concurrent_calls, active_calls)
        # Simulate some async work
        await asyncio.sleep(0.01)
        active_calls -= 1
        return LlmPromptResponse(model_id="gpt-4o-mini", output_text="Translation")

    ctx.mock_runtime = MagicMock()
    ctx.mock_runtime.run_prompt = mock_run_prompt  # type: ignore[assignment]


@given("a concurrency limit of 2")
def given_concurrency_limit(ctx: MTLBaselineContext) -> None:
    """Set concurrency limit to 2.

    Args:
        ctx: Context to update.
    """
    ctx.concurrency_limit = 2


@when("I generate MTL baseline translations")
@pytest.mark.asyncio
async def when_generate_baseline(ctx: MTLBaselineContext) -> None:
    """Generate MTL baseline translations.

    Args:
        ctx: Context with sources, runtime, and settings.
    """
    assert ctx.sources is not None
    assert ctx.runtime_settings is not None
    assert ctx.mock_runtime is not None

    ctx.generator = MTLBaselineGenerator(
        runtime=ctx.mock_runtime,
        runtime_settings=ctx.runtime_settings,
        api_key="test-key",
        concurrency_limit=ctx.concurrency_limit,
    )

    ctx.results = await ctx.generator.generate_baseline(ctx.sources)


@then("all prompts use minimal translation structure")
def then_prompts_minimal(ctx: MTLBaselineContext) -> None:
    """Assert all prompts use minimal translation structure.

    Args:
        ctx: Context with captured prompts.
    """
    assert ctx.captured_prompts is not None
    assert len(ctx.captured_prompts) > 0

    for prompt in ctx.captured_prompts:
        assert "Translate the following Japanese text to English:" in prompt


@then("no prompts include context injection")
def then_no_context(ctx: MTLBaselineContext) -> None:
    """Assert no prompts include context injection.

    Args:
        ctx: Context with captured prompts.
    """
    assert ctx.captured_prompts is not None

    for prompt in ctx.captured_prompts:
        # Verify no context keywords
        assert "context" not in prompt.lower()
        assert "previous" not in prompt.lower()


@then("all results are valid TranslatedLine objects")
def then_valid_schema(ctx: MTLBaselineContext) -> None:
    """Assert all results are valid TranslatedLine objects.

    Args:
        ctx: Context with results.
    """
    assert ctx.results is not None
    assert ctx.sources is not None
    assert len(ctx.results) == len(ctx.sources)

    for result, source in zip(ctx.results, ctx.sources, strict=True):
        # Verify schema fields
        assert result.scene_id == source.scene_id
        assert result.line_id == source.line_id
        assert result.source_text == source.text
        assert isinstance(result.text, str)
        assert len(result.text) > 0


@then("all results are marked as MTL baseline")
def then_mtl_marked(ctx: MTLBaselineContext) -> None:
    """Assert all results are marked as MTL baseline.

    Args:
        ctx: Context with results.
    """
    assert ctx.results is not None

    for result in ctx.results:
        assert result.metadata["mtl_baseline"]  # type: ignore[index] is True
        assert result.metadata["model"]  # type: ignore[index] == "gpt-4o-mini"


@then("concurrent calls never exceed the limit")
def then_concurrency_respected(ctx: MTLBaselineContext) -> None:
    """Assert concurrent calls never exceed the configured limit.

    Args:
        ctx: Context with max_concurrent_calls tracking.
    """
    assert ctx.max_concurrent_calls <= ctx.concurrency_limit


@then("all translations complete successfully")
def then_all_complete(ctx: MTLBaselineContext) -> None:
    """Assert all translations completed successfully.

    Args:
        ctx: Context with results and sources.
    """
    assert ctx.results is not None
    assert ctx.sources is not None
    assert len(ctx.results) == len(ctx.sources)
