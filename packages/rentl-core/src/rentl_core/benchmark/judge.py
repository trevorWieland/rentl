"""LLM-as-judge for translation quality evaluation.

Scores translations using rubric-based evaluation with configurable judge model.
Supports reference-based, reference-free, and head-to-head comparison modes.
"""

import asyncio
import json
import random
from collections.abc import Awaitable, Callable
from typing import Literal

from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    RubricDimension,
)
from rentl_schemas.io import TranslatedLine
from rentl_schemas.llm import LlmPromptRequest, LlmRuntimeSettings


class RubricJudge:
    """LLM-as-judge for rubric-based translation evaluation.

    Scores translations on accuracy, style fidelity, and consistency using
    structured prompts and output parsing. Supports multiple scoring modes.
    """

    def __init__(
        self,
        runtime: LlmRuntimeProtocol,
        runtime_settings: LlmRuntimeSettings,
        api_key: str,
        concurrency_limit: int = 5,
    ) -> None:
        """Initialize rubric judge.

        Args:
            runtime: LLM runtime adapter
            runtime_settings: Runtime settings (endpoint, model, retry)
            api_key: API key for LLM endpoint
            concurrency_limit: Maximum concurrent judging requests
        """
        self.runtime = runtime
        self.runtime_settings = runtime_settings
        self.api_key = api_key
        self.concurrency_limit = concurrency_limit
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    def _build_head_to_head_prompt(
        self, source_text: str, translation_a: str, translation_b: str
    ) -> str:
        """Build head-to-head comparison prompt.

        Args:
            source_text: Original source language text
            translation_a: First translation (label "A")
            translation_b: Second translation (label "B")

        Returns:
            Structured comparison prompt
        """
        return f"""You are comparing two translations from Japanese to English.

Source text (Japanese):
{source_text}

Translation A:
{translation_a}

Translation B:
{translation_b}

Compare these translations and determine which is better overall,
plus which wins on each dimension.

Dimensions:
1. ACCURACY: Which translation more faithfully conveys the source meaning?
2. STYLE FIDELITY: Which translation reads more naturally and appropriately in English?
3. CONSISTENCY: Which translation uses more consistent terminology and naming?

For ties, use "tie" if both translations are equally good or equally flawed.

Provide your evaluation in this exact JSON format:
{{
    "overall_winner": "<A|B|tie>",
    "reasoning": "<explanation for overall winner>",
    "dimension_winners": {{
        "accuracy": "<A|B|tie>",
        "style_fidelity": "<A|B|tie>",
        "consistency": "<A|B|tie>"
    }}
}}"""

    def _parse_head_to_head(
        self, response_text: str
    ) -> tuple[
        Literal["A", "B", "tie"], str, dict[RubricDimension, Literal["A", "B", "tie"]]
    ]:
        """Parse head-to-head comparison response.

        Args:
            response_text: Raw LLM response containing JSON

        Returns:
            Tuple of (overall_winner, reasoning, dimension_winners)

        Raises:
            ValueError: If parsing fails or format is invalid
        """
        # Extract JSON from response (handle markdown code blocks)
        response_text = response_text.strip()
        if "```json" in response_text:
            start = response_text.index("```json") + 7
            end = response_text.index("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.index("```") + 3
            end = response_text.index("```", start)
            response_text = response_text[start:end].strip()

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse judge response as JSON: {e}") from e

        if "overall_winner" not in data or "reasoning" not in data:
            raise ValueError("Missing 'overall_winner' or 'reasoning' in response")

        overall_winner_str = data["overall_winner"]
        if overall_winner_str not in ("A", "B", "tie"):
            raise ValueError(f"Invalid overall_winner: {overall_winner_str}")
        overall_winner: Literal["A", "B", "tie"] = overall_winner_str

        reasoning = data["reasoning"]

        if "dimension_winners" not in data:
            raise ValueError("Missing 'dimension_winners' in response")

        dimension_winners: dict[RubricDimension, Literal["A", "B", "tie"]] = {}
        for dim in RubricDimension:
            if dim.value not in data["dimension_winners"]:
                raise ValueError(
                    f"Missing dimension winner for {dim.value} in response"
                )
            winner_str = data["dimension_winners"][dim.value]
            if winner_str not in ("A", "B", "tie"):
                raise ValueError(f"Invalid winner for {dim.value}: {winner_str}")
            winner_typed: Literal["A", "B", "tie"] = winner_str
            dimension_winners[dim] = winner_typed

        return overall_winner, reasoning, dimension_winners

    async def compare_head_to_head(
        self,
        line_id: str,
        source_text: str,
        translation_1: str,
        translation_2: str,
        candidate_1_name: str,
        candidate_2_name: str,
        randomize_order: bool = True,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> HeadToHeadResult:
        """Compare two translations head-to-head.

        Args:
            line_id: Unique identifier for this line
            source_text: Original source language text
            translation_1: First translation to compare
            translation_2: Second translation to compare
            candidate_1_name: Name of first candidate
            candidate_2_name: Name of second candidate
            randomize_order: Whether to randomize A/B assignment (reduces position bias)
            progress_callback: Optional callback for progress reporting

        Returns:
            HeadToHeadResult with winner and reasoning
        """
        async with self._semaphore:
            # Randomize assignment to reduce position bias
            if randomize_order and random.random() < 0.5:
                a_is_1 = False
                translation_a = translation_2
                translation_b = translation_1
            else:
                a_is_1 = True
                translation_a = translation_1
                translation_b = translation_2

            prompt = self._build_head_to_head_prompt(
                source_text, translation_a, translation_b
            )

            request = LlmPromptRequest(
                runtime=self.runtime_settings,
                prompt=prompt,
                system_prompt=None,
            )

            response = await self.runtime.run_prompt(request, api_key=self.api_key)
            overall_winner, reasoning, dimension_winners = self._parse_head_to_head(
                response.output_text
            )

            # Map A/B back to translation_1/translation_2
            final_overall_winner: Literal["A", "B", "tie"] = overall_winner
            final_dimension_winners: dict[RubricDimension, Literal["A", "B", "tie"]] = (
                dimension_winners
            )
            if not a_is_1:
                # A was translation_2, B was translation_1, so swap
                winner_map: dict[str, Literal["A", "B", "tie"]] = {
                    "A": "B",
                    "B": "A",
                    "tie": "tie",
                }
                final_overall_winner = winner_map[overall_winner]
                final_dimension_winners = {
                    dim: winner_map[winner] for dim, winner in dimension_winners.items()
                }

            if progress_callback:
                await progress_callback(line_id)

            return HeadToHeadResult(
                line_id=line_id,
                source_text=source_text,
                candidate_a_name=candidate_1_name,
                candidate_b_name=candidate_2_name,
                translation_a=translation_1,
                translation_b=translation_2,
                winner=final_overall_winner,
                reasoning=reasoning,
                dimension_winners=final_dimension_winners,
            )

    async def compare_batch_head_to_head(
        self,
        translations_1: list[TranslatedLine],
        translations_2: list[TranslatedLine],
        candidate_1_name: str,
        candidate_2_name: str,
        randomize_order: bool = True,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> list[HeadToHeadResult]:
        """Compare two sets of translations head-to-head in parallel.

        Args:
            translations_1: First set of translations
            translations_2: Second set of translations (must match line_ids)
            candidate_1_name: Name of first candidate
            candidate_2_name: Name of second candidate
            randomize_order: Whether to randomize A/B assignment per line
            progress_callback: Optional callback for progress reporting

        Returns:
            List of head-to-head results for all line pairs

        Raises:
            ValueError: If translation sets don't match by line_id
        """
        # Build lookup for translations_2
        trans2_map = {t.line_id: t for t in translations_2}

        tasks = []
        for trans1 in translations_1:
            trans2 = trans2_map.get(trans1.line_id)
            if trans2 is None:
                raise ValueError(
                    f"Line {trans1.line_id} not found in second translation set"
                )

            tasks.append(
                self.compare_head_to_head(
                    line_id=trans1.line_id,
                    source_text=trans1.source_text or "",
                    translation_1=trans1.text,
                    translation_2=trans2.text,
                    candidate_1_name=candidate_1_name,
                    candidate_2_name=candidate_2_name,
                    randomize_order=randomize_order,
                    progress_callback=progress_callback,
                )
            )

        return await asyncio.gather(*tasks)
