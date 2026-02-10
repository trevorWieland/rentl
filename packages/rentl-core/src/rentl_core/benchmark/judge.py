"""LLM-as-judge for translation quality evaluation.

Compares translations head-to-head using rubric-based evaluation with configurable
judge model. Evaluates accuracy, style fidelity, and consistency with source text.
"""

import asyncio
import json
import random
import re
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, Field

from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    RubricDimension,
)
from rentl_schemas.io import TranslatedLine
from rentl_schemas.llm import LlmPromptRequest, LlmRuntimeSettings


class JudgeOutput(BaseModel):
    """Structured output schema for judge response."""

    overall_winner: Literal["A", "B", "tie"] = Field(
        ..., description="Overall winner of the comparison"
    )
    reasoning: str = Field(..., description="Explanation for overall winner")
    dimension_winners: dict[str, Literal["A", "B", "tie"]] = Field(
        ..., description="Winners per dimension (accuracy, style_fidelity, consistency)"
    )


class RubricJudge:
    """LLM-as-judge for rubric-based translation evaluation.

    Compares translations pairwise on accuracy, style fidelity, and consistency
    using structured prompts and output parsing. Supports randomized A/B order
    to reduce position bias.
    """

    def __init__(
        self,
        runtime: LlmRuntimeProtocol,
        runtime_settings: LlmRuntimeSettings,
        api_key: str,
        concurrency_limit: int = 5,
        max_retries: int = 3,
    ) -> None:
        """Initialize rubric judge.

        Args:
            runtime: LLM runtime adapter
            runtime_settings: Runtime settings (endpoint, model, retry)
            api_key: API key for LLM endpoint
            concurrency_limit: Maximum concurrent judging requests
            max_retries: Maximum retries per comparison on parse failure
        """
        self.runtime = runtime
        self.runtime_settings = runtime_settings
        self.api_key = api_key
        self.concurrency_limit = concurrency_limit
        self.max_retries = max_retries
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
        return f"""You are comparing two translations of the same source text.

Source text:
{source_text}

Translation A:
{translation_a}

Translation B:
{translation_b}

Compare these translations and determine which is better overall,
plus which wins on each dimension.

Dimensions:
1. ACCURACY: Which translation more faithfully conveys the source meaning?
2. STYLE FIDELITY: Which translation reads more naturally and appropriately
   in the target language?
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

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON content from response text with fallback strategies.

        Args:
            text: Raw response text possibly containing JSON

        Returns:
            Extracted JSON string (best-effort extraction, may not be valid JSON)
        """
        text = text.strip()

        # Strategy 1: Markdown code blocks with json tag
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()

        # Strategy 2: Markdown code blocks without json tag
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()

        # Strategy 3: Find JSON object via regex (handles reasoning prefix/suffix)
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            # Try parsing each match to find valid JSON
            for match in matches:
                try:
                    json.loads(match)
                    return match
                except json.JSONDecodeError:
                    continue

        # Strategy 4: Return text as-is and let JSON parser fail with clear error
        return text

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
        # Extract JSON from response with multiple fallback strategies
        json_text = self._extract_json_from_text(response_text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse judge response as JSON: {e}\n"
                f"Extracted text: {json_text[:200]}..."
            ) from e

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
        """Compare two translations head-to-head with retry on parse failure.

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

        Raises:
            ValueError: If parsing fails after all retries
        """
        async with self._semaphore:
            last_error: Exception | None = None

            for attempt in range(self.max_retries):
                try:
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
                        result_schema=JudgeOutput,
                    )

                    response = await self.runtime.run_prompt(
                        request, api_key=self.api_key
                    )

                    # Use structured output if available, otherwise fall back to parsing
                    if response.structured_output is not None:
                        judge_output = response.structured_output
                        if not isinstance(judge_output, JudgeOutput):
                            raise ValueError(
                                f"Expected JudgeOutput but got {type(judge_output)}"
                            )
                        overall_winner = judge_output.overall_winner
                        reasoning = judge_output.reasoning
                        # Convert string keys to RubricDimension enum
                        dimension_winners: dict[
                            RubricDimension, Literal["A", "B", "tie"]
                        ] = {}
                        for dim_str, winner in judge_output.dimension_winners.items():
                            dim = RubricDimension(dim_str)
                            dimension_winners[dim] = winner
                    else:
                        # Fallback to text parsing for backwards compatibility
                        overall_winner, reasoning, dimension_winners = (
                            self._parse_head_to_head(response.output_text)
                        )

                    # Map A/B back to translation_1/translation_2
                    final_overall_winner: Literal["A", "B", "tie"] = overall_winner
                    final_dimension_winners: dict[
                        RubricDimension, Literal["A", "B", "tie"]
                    ] = dimension_winners
                    if not a_is_1:
                        # A was translation_2, B was translation_1, so swap
                        winner_map: dict[str, Literal["A", "B", "tie"]] = {
                            "A": "B",
                            "B": "A",
                            "tie": "tie",
                        }
                        final_overall_winner = winner_map[overall_winner]
                        final_dimension_winners = {
                            dim: winner_map[winner]
                            for dim, winner in dimension_winners.items()
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
                except ValueError as e:
                    last_error = e
                    # On parse failure, retry with a different randomization
                    # This gives the model another chance to produce valid output
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                    # Final attempt failed, re-raise
                    raise ValueError(
                        f"Failed to parse judge response for line {line_id} "
                        f"after {self.max_retries} attempts: {last_error}"
                    ) from last_error

            # Should never reach here due to raise in loop
            raise ValueError(
                f"Failed to compare line {line_id} after {self.max_retries} attempts"
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
