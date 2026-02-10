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
    LineScore,
    RubricDimension,
    RubricScore,
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

    def _build_reference_based_prompt(
        self, source_text: str, reference: str, candidate: str
    ) -> str:
        """Build reference-based evaluation prompt.

        Args:
            source_text: Original source language text
            reference: Known-good reference translation
            candidate: Translation to evaluate

        Returns:
            Structured evaluation prompt with rubric
        """
        return f"""You are evaluating a translation from Japanese to English.

Source text (Japanese):
{source_text}

Reference translation (known-good English):
{reference}

Candidate translation (being evaluated):
{candidate}

Evaluate the candidate translation on these three dimensions using a 1-5 scale:

1. ACCURACY (1=poor, 5=excellent): Does the candidate faithfully convey
   the meaning of the source text? Compare against source and reference.

2. STYLE FIDELITY (1=poor, 5=excellent): Is the candidate natural English
   with appropriate register and voice? Match reference style quality?

3. CONSISTENCY (1=poor, 5=excellent): Does the candidate use consistent
   terminology and naming conventions?

Provide your evaluation in this exact JSON format:
{{
    "accuracy": {{
        "score": <1-5>,
        "reasoning": "<explanation>"
    }},
    "style_fidelity": {{
        "score": <1-5>,
        "reasoning": "<explanation>"
    }},
    "consistency": {{
        "score": <1-5>,
        "reasoning": "<explanation>"
    }}
}}"""

    def _build_reference_free_prompt(self, source_text: str, candidate: str) -> str:
        """Build reference-free evaluation prompt.

        Args:
            source_text: Original source language text
            candidate: Translation to evaluate

        Returns:
            Structured evaluation prompt with rubric (no reference)
        """
        return f"""You are evaluating a translation from Japanese to English.

Source text (Japanese):
{source_text}

Candidate translation (English):
{candidate}

Evaluate the translation on these three dimensions using a 1-5 scale:

1. ACCURACY (1=poor, 5=excellent): Does the translation faithfully convey
   the meaning of the source text? Consider semantic completeness.

2. STYLE FIDELITY (1=poor, 5=excellent): Is the translation natural
   English with appropriate register and voice? Does it read fluently?

3. CONSISTENCY (1=poor, 5=excellent): Does the translation use
   consistent terminology and naming conventions?

Provide your evaluation in this exact JSON format:
{{
    "accuracy": {{
        "score": <1-5>,
        "reasoning": "<explanation>"
    }},
    "style_fidelity": {{
        "score": <1-5>,
        "reasoning": "<explanation>"
    }},
    "consistency": {{
        "score": <1-5>,
        "reasoning": "<explanation>"
    }}
}}"""

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

    def _parse_rubric_scores(self, response_text: str) -> list[RubricScore]:
        """Parse judge response into rubric scores.

        Args:
            response_text: Raw LLM response containing JSON

        Returns:
            List of rubric scores for each dimension

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

        scores = []
        for dim in RubricDimension:
            if dim.value not in data:
                raise ValueError(f"Missing dimension {dim.value} in judge response")

            dim_data = data[dim.value]
            if "score" not in dim_data or "reasoning" not in dim_data:
                raise ValueError(
                    f"Dimension {dim.value} missing 'score' or 'reasoning'"
                )

            scores.append(
                RubricScore(
                    dimension=dim,
                    score=dim_data["score"],
                    reasoning=dim_data["reasoning"],
                )
            )

        return scores

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

        dimension_winners: dict[RubricDimension, Literal["A", "B", "tie"]] = {}
        if "dimension_winners" in data:
            for dim in RubricDimension:
                if dim.value in data["dimension_winners"]:
                    winner_str = data["dimension_winners"][dim.value]
                    if winner_str not in ("A", "B", "tie"):
                        raise ValueError(
                            f"Invalid winner for {dim.value}: {winner_str}"
                        )
                    winner_typed: Literal["A", "B", "tie"] = winner_str
                    dimension_winners[dim] = winner_typed

        return overall_winner, reasoning, dimension_winners

    async def score_translation(
        self,
        line_id: str,
        source_text: str,
        translation: str,
        reference: str | None = None,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> LineScore:
        """Score a single translation using rubric evaluation.

        Args:
            line_id: Unique identifier for this line
            source_text: Original source language text
            translation: Translation to evaluate
            reference: Optional reference translation (enables reference-based mode)
            progress_callback: Optional callback for progress reporting

        Returns:
            LineScore with rubric scores for all dimensions
        """
        async with self._semaphore:
            # Choose prompt based on reference availability
            if reference is not None:
                prompt = self._build_reference_based_prompt(
                    source_text, reference, translation
                )
            else:
                prompt = self._build_reference_free_prompt(source_text, translation)

            request = LlmPromptRequest(
                runtime=self.runtime_settings,
                prompt=prompt,
                system_prompt=None,
            )

            response = await self.runtime.run_prompt(request, api_key=self.api_key)
            scores = self._parse_rubric_scores(response.output_text)

            if progress_callback:
                await progress_callback(line_id)

            return LineScore(
                line_id=line_id,
                source_text=source_text,
                translation=translation,
                reference=reference,
                scores=scores,
            )

    async def score_batch(
        self,
        translations: list[TranslatedLine],
        references: dict[str, str] | None = None,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> list[LineScore]:
        """Score multiple translations in parallel.

        Args:
            translations: Translations to evaluate
            references: Optional reference translations keyed by line_id
            progress_callback: Optional callback for progress reporting

        Returns:
            List of line scores for all translations
        """
        tasks = []
        for trans in translations:
            reference = references.get(trans.line_id) if references else None
            tasks.append(
                self.score_translation(
                    line_id=trans.line_id,
                    source_text=trans.source_text or "",
                    translation=trans.text,
                    reference=reference,
                    progress_callback=progress_callback,
                )
            )
        return await asyncio.gather(*tasks)

    async def compare_head_to_head(
        self,
        line_id: str,
        source_text: str,
        translation_1: str,
        translation_2: str,
        randomize_order: bool = True,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> HeadToHeadResult:
        """Compare two translations head-to-head.

        Args:
            line_id: Unique identifier for this line
            source_text: Original source language text
            translation_1: First translation to compare
            translation_2: Second translation to compare
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
        randomize_order: bool = True,
        progress_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> list[HeadToHeadResult]:
        """Compare two sets of translations head-to-head in parallel.

        Args:
            translations_1: First set of translations
            translations_2: Second set of translations (must match line_ids)
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
                    randomize_order=randomize_order,
                    progress_callback=progress_callback,
                )
            )

        return await asyncio.gather(*tasks)
