"""MTL baseline generator for benchmark comparisons.

Provides minimal single-shot translation without rentl pipeline features
(no context, no QA, no edit phases) for apples-to-apples comparison.
"""

import asyncio
from collections.abc import Awaitable, Callable

from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.llm import LlmPromptRequest, LlmRuntimeSettings


class MTLBaselineGenerator:
    """Generate minimal translation baselines for benchmark comparison.

    Uses a simple "translate this" prompt with no context injection, QA,
    or edit phases to establish a baseline for measuring rentl pipeline value.
    """

    def __init__(
        self,
        runtime: LlmRuntimeProtocol,
        runtime_settings: LlmRuntimeSettings,
        api_key: str,
        concurrency_limit: int = 10,
    ) -> None:
        """Initialize MTL baseline generator.

        Args:
            runtime: LLM runtime adapter
            runtime_settings: Runtime settings (endpoint, model, retry)
            api_key: API key for LLM endpoint
            concurrency_limit: Maximum concurrent translation requests
        """
        self.runtime = runtime
        self.runtime_settings = runtime_settings
        self.api_key = api_key
        self.concurrency_limit = concurrency_limit
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    def _build_prompt(self, source_line: SourceLine) -> str:
        """Build minimal translation prompt.

        Args:
            source_line: Source line to translate

        Returns:
            Minimal single-shot translation prompt
        """
        return (
            f"Translate the following Japanese text to English:\n\n{source_line.text}"
        )

    async def _translate_one(
        self,
        source_line: SourceLine,
        progress_callback: Callable[[SourceLine], Awaitable[None]] | None = None,
    ) -> TranslatedLine:
        """Translate a single line with minimal prompt.

        Args:
            source_line: Source line to translate
            progress_callback: Optional callback for progress reporting

        Returns:
            Translated line with MTL baseline text
        """
        async with self._semaphore:
            prompt = self._build_prompt(source_line)

            request = LlmPromptRequest(
                runtime=self.runtime_settings,
                prompt=prompt,
                system_prompt=None,
            )

            # Single-shot translation call
            response = await self.runtime.run_prompt(request, api_key=self.api_key)
            translation_text = response.output_text.strip()

            if progress_callback:
                await progress_callback(source_line)

            return TranslatedLine(
                scene_id=source_line.scene_id,
                line_id=source_line.line_id,
                text=translation_text,
                source_text=source_line.text,
                speaker=source_line.speaker,
                metadata={
                    "mtl_baseline": True,
                    "model": self.runtime_settings.model.model_id,
                },
            )

    async def generate_baseline(
        self,
        source_lines: list[SourceLine],
        progress_callback: Callable[[SourceLine], Awaitable[None]] | None = None,
    ) -> list[TranslatedLine]:
        """Generate MTL baseline translations for all source lines.

        Args:
            source_lines: Source lines to translate
            progress_callback: Optional callback for progress reporting

        Returns:
            List of translated lines with MTL baseline text
        """
        tasks = [self._translate_one(line, progress_callback) for line in source_lines]
        return await asyncio.gather(*tasks)
