"""LLM-as-judge for translation quality evaluation.

Compares translations head-to-head using rubric-based evaluation with configurable
judge model. Evaluates accuracy, style fidelity, and consistency with source text.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Literal, cast

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from rentl_llm.provider_factory import create_model
from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    RubricDimension,
)
from rentl_schemas.config import OpenRouterProviderRoutingConfig
from rentl_schemas.io import TranslatedLine


class JudgeOutput(BaseModel):
    """Structured output schema for judge response."""

    overall_winner: Literal["A", "B", "tie"] = Field(
        ..., description="Overall winner of the comparison"
    )
    reasoning: str = Field(..., description="Explanation for overall winner")
    accuracy_winner: Literal["A", "B", "tie"] = Field(
        ..., description="Winner for accuracy dimension"
    )
    style_fidelity_winner: Literal["A", "B", "tie"] = Field(
        ..., description="Winner for style fidelity dimension"
    )
    consistency_winner: Literal["A", "B", "tie"] = Field(
        ..., description="Winner for consistency dimension"
    )


class RubricJudge:
    """LLM-as-judge for rubric-based translation evaluation.

    Compares translations pairwise on accuracy, style fidelity, and consistency
    using pydantic-ai Agent with structured output. Supports randomized A/B order
    to reduce position bias.
    """

    def __init__(
        self,
        model_id: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
        concurrency_limit: int = 5,
        openrouter_require_parameters: bool = True,
    ) -> None:
        """Initialize rubric judge.

        Args:
            model_id: Model ID to use for judging
            base_url: Base URL for LLM endpoint
            api_key: API key for LLM endpoint
            temperature: Sampling temperature (default 0.7)
            max_output_tokens: Maximum output tokens per request
            concurrency_limit: Maximum concurrent judging requests
            openrouter_require_parameters: Enable OpenRouter routing constraints
        """
        self.model_id = model_id
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.concurrency_limit = concurrency_limit
        self._semaphore = asyncio.Semaphore(concurrency_limit)

        # Create model/provider via centralized factory
        openrouter_config = OpenRouterProviderRoutingConfig(
            require_parameters=openrouter_require_parameters,
        )
        self.model, self.model_settings = create_model(
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            openrouter_provider=openrouter_config,
        )

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

For ties, use "tie" if both translations are equally good or equally flawed."""

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
        """Compare two translations head-to-head using pydantic-ai Agent.

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

            # Create pydantic-ai agent with JudgeOutput as structured output type
            agent = Agent(
                model=self.model,
                output_type=JudgeOutput,
                output_retries=5,  # Pydantic-ai handles retries on validation failure
            )

            # Run agent with prompt - structured output is guaranteed
            result = await agent.run(prompt, model_settings=self.model_settings)
            judge_output = cast(JudgeOutput, result.output)

            # Extract winners from structured output
            overall_winner = judge_output.overall_winner
            reasoning = judge_output.reasoning
            dimension_winners: dict[RubricDimension, Literal["A", "B", "tie"]] = {
                RubricDimension.ACCURACY: judge_output.accuracy_winner,
                RubricDimension.STYLE_FIDELITY: judge_output.style_fidelity_winner,
                RubricDimension.CONSISTENCY: judge_output.consistency_winner,
            }

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

            # Record which candidate was presented as "A" for reasoning interpretation
            presented_as_a = candidate_1_name if a_is_1 else candidate_2_name

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
                presented_as_a=presented_as_a,
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
