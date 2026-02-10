"""Unit tests for MTL baseline generator."""

from unittest.mock import AsyncMock, MagicMock

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


class TestMTLBaselineGenerator:
    """Test MTL baseline generator prompt construction and output validation."""

    def test_build_prompt_structure(self, runtime_settings: LlmRuntimeSettings) -> None:
        """Test minimal prompt construction without context or QA."""
        mock_runtime = MagicMock()
        generator = MTLBaselineGenerator(
            runtime=mock_runtime,
            runtime_settings=runtime_settings,
            api_key="test-key",
        )

        source = SourceLine(
            scene_id="test_1",
            line_id="line_1",
            text="こんにちは、世界。",
            speaker=None,
        )

        prompt = generator._build_prompt(source)

        # Verify minimal prompt structure
        assert "Translate the following Japanese text to English:" in prompt
        assert source.text in prompt
        # Verify no context injection
        assert "context" not in prompt.lower()
        assert "previous" not in prompt.lower()
        # Verify simple structure
        assert prompt.count("\n") <= 3  # Header + blank + text

    def test_build_prompt_with_speaker(
        self, runtime_settings: LlmRuntimeSettings
    ) -> None:
        """Test prompt construction preserves focus on text, not speaker."""
        mock_runtime = MagicMock()
        generator = MTLBaselineGenerator(
            runtime=mock_runtime,
            runtime_settings=runtime_settings,
            api_key="test-key",
        )

        source = SourceLine(
            scene_id="test_1",
            line_id="line_1",
            text="待ってください!",
            speaker="emi",
        )

        prompt = generator._build_prompt(source)

        # Speaker should not be in the prompt (MTL is raw text-to-text)
        assert "emi" not in prompt.lower()
        assert source.text in prompt

    @pytest.mark.asyncio
    async def test_translate_one_output_schema(
        self, runtime_settings: LlmRuntimeSettings
    ) -> None:
        """Test single line translation produces valid TranslatedLine."""
        mock_runtime = MagicMock()
        mock_runtime.run_prompt = AsyncMock(
            return_value=LlmPromptResponse(
                model_id="gpt-4o-mini",
                output_text="Good morning.",
            )
        )

        generator = MTLBaselineGenerator(
            runtime=mock_runtime,
            runtime_settings=runtime_settings,
            api_key="test-key",
        )

        source = SourceLine(
            scene_id="test_1",
            line_id="line_1",
            text="おはよう。",
            speaker="hi",
        )

        result = await generator._translate_one(source)

        # Verify output schema
        assert result.scene_id == source.scene_id
        assert result.line_id == source.line_id
        assert result.text == "Good morning."
        assert result.source_text == source.text
        assert result.speaker == source.speaker
        assert result.metadata["mtl_baseline"] is True  # type: ignore[index]
        assert result.metadata["model"] == "gpt-4o-mini"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_translate_one_strips_whitespace(
        self, runtime_settings: LlmRuntimeSettings
    ) -> None:
        """Test translation output is stripped of leading/trailing whitespace."""
        mock_runtime = MagicMock()
        mock_runtime.run_prompt = AsyncMock(
            return_value=LlmPromptResponse(
                model_id="gpt-4o-mini",
                output_text="  Test.  \n",
            )
        )

        generator = MTLBaselineGenerator(
            runtime=mock_runtime,
            runtime_settings=runtime_settings,
            api_key="test-key",
        )

        source = SourceLine(
            scene_id="test_1",
            line_id="line_1",
            text="テスト。",
            speaker=None,
        )

        result = await generator._translate_one(source)

        assert result.text == "Test."  # Stripped

    @pytest.mark.asyncio
    async def test_generate_baseline_batch(
        self, runtime_settings: LlmRuntimeSettings
    ) -> None:
        """Test batch baseline generation preserves order and completeness."""
        call_count = 0

        async def mock_run_prompt(  # noqa: RUF029
            request: LlmPromptRequest, api_key: str
        ) -> LlmPromptResponse:
            nonlocal call_count
            call_count += 1
            return LlmPromptResponse(
                model_id="gpt-4o-mini",
                output_text=f"Translation {call_count}",
            )

        mock_runtime = MagicMock()
        mock_runtime.run_prompt = mock_run_prompt

        generator = MTLBaselineGenerator(
            runtime=mock_runtime,
            runtime_settings=runtime_settings,
            api_key="test-key",
            concurrency_limit=2,
        )

        sources = [
            SourceLine(
                scene_id="test_1",
                line_id="line_1",
                text="一行目。",
                speaker=None,
            ),
            SourceLine(
                scene_id="test_1",
                line_id="line_2",
                text="二行目。",
                speaker="mu",
            ),
            SourceLine(
                scene_id="test_1",
                line_id="line_3",
                text="三行目。",
                speaker=None,
            ),
        ]

        results = await generator.generate_baseline(sources)

        # Verify all lines translated
        assert len(results) == 3
        # Verify order preserved by scene/line IDs
        assert results[0].scene_id == "test_1"
        assert results[0].line_id == "line_1"
        assert results[1].line_id == "line_2"
        assert results[2].line_id == "line_3"
        # Verify all have MTL metadata
        for r in results:
            assert r.metadata["mtl_baseline"] is True  # type: ignore[index]
            assert r.metadata["model"] == "gpt-4o-mini"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_progress_callback_invoked(
        self, runtime_settings: LlmRuntimeSettings
    ) -> None:
        """Test progress callback is called for each translated line."""
        mock_runtime = MagicMock()
        mock_runtime.run_prompt = AsyncMock(
            return_value=LlmPromptResponse(
                model_id="gpt-4o-mini",
                output_text="Translation",
            )
        )

        generator = MTLBaselineGenerator(
            runtime=mock_runtime,
            runtime_settings=runtime_settings,
            api_key="test-key",
        )

        sources = [
            SourceLine(
                scene_id="test_1",
                line_id="line_1",
                text="一",
                speaker=None,
            ),
            SourceLine(
                scene_id="test_1",
                line_id="line_2",
                text="二",
                speaker=None,
            ),
        ]

        # Track progress callback invocations
        progress_calls: list[SourceLine] = []

        async def progress_callback(line: SourceLine) -> None:  # noqa: RUF029
            progress_calls.append(line)

        await generator.generate_baseline(sources, progress_callback)

        # Verify callback invoked for each line
        assert len(progress_calls) == 2
        assert progress_calls[0].line_id == "line_1"
        assert progress_calls[1].line_id == "line_2"
