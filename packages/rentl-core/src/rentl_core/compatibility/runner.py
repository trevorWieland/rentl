"""Shared verification runner for multi-model compatibility testing.

Both ``rentl verify-models`` CLI and the pytest compatibility test suite
use this runner to verify models through a mini 5-phase pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import os

from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from rentl_core.compatibility.loader import (
    ModelLoadError,
    ModelUnloadError,
    load_lm_studio_model,
    unload_lm_studio_model,
)
from rentl_core.compatibility.types import (
    ModelVerificationResult,
    PhaseResult,
    PhaseVerificationStatus,
    RegistryVerificationResult,
)
from rentl_llm.provider_factory import create_model
from rentl_schemas.base import BaseSchema
from rentl_schemas.compatibility import (
    VerifiedModelEntry,
    VerifiedModelRegistry,
)
from rentl_schemas.config import ModelEndpointConfig
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import (
    IdiomAnnotationList,
    SceneSummary,
    StyleGuideReviewList,
    TranslationResultLine,
    TranslationResultList,
)
from rentl_schemas.primitives import PhaseName
from rentl_schemas.qa import LineEdit

_log = logging.getLogger(__name__)

# Verification phases produce tiny JSON; 1024 tokens is generous.  The old
# default (4096) let models ramble into malformed/verbose output, wasting
# time and triggering output-validation retries.
_DEFAULT_MAX_OUTPUT_TOKENS = 1024

# ---------------------------------------------------------------------------
# Golden input data for the mini-pipeline
# ---------------------------------------------------------------------------

GOLDEN_SOURCE_LINE = SourceLine(
    line_id="scene_001_0001",
    route_id="common_0",
    scene_id="scene_001",
    text="春の朝、桜の花びらが風に舞う学園の門。",
    metadata={"is_choice": False, "is_dialogue": False},
)

_TARGET_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# Minimal output schemas for verification
# Each phase uses the real pipeline output schema so we validate that the
# model can produce structured output matching what the pipeline expects.
# ---------------------------------------------------------------------------


# Context phase — SceneSummary list wrapper
class ContextOutput(BaseSchema):
    """Minimal context phase output for verification."""

    scene_summaries: list[SceneSummary] = Field(
        ...,
        min_length=1,
        description="Scene summaries from context analysis",
    )


# Edit phase — line edit list wrapper
class EditOutput(BaseSchema):
    """Minimal edit phase output for verification."""

    edited_lines: list[TranslationResultLine] = Field(
        ...,
        min_length=1,
        description="Edited translation lines",
    )
    changes: list[LineEdit] = Field(
        default_factory=list,
        description="Line edit records",
    )


# ---------------------------------------------------------------------------
# Phase prompts — kept minimal; we only care about structured output success
# ---------------------------------------------------------------------------

PHASE_CONFIGS: list[tuple[PhaseName, str, str, type[BaseSchema]]] = [
    (
        PhaseName.CONTEXT,
        "You are a scene summarizer. Respond with minimal JSON only.",
        (
            "Summarize this scene in one sentence.\n"
            "Source: {text}\n"
            "Respond with exactly: "
            '{{"scene_summaries": [{{"scene_id": "scene_001", '
            '"summary": "<1 sentence>", "characters": []}}]}}'
        ),
        ContextOutput,
    ),
    (
        PhaseName.PRETRANSLATION,
        "You are an idiom annotator. Respond with minimal JSON only.",
        (
            "List idioms in this line (empty list if none).\n"
            "Source: {text}\n"
            "Respond with exactly: "
            '{{"reviews": [{{"line_id": "{line_id}", "idioms": []}}]}}'
        ),
        IdiomAnnotationList,
    ),
    (
        PhaseName.TRANSLATE,
        "You are a Japanese-to-English translator. Respond with minimal JSON only.",
        (
            "Translate to English.\n"
            "Source (line_id: {line_id}): {text}\n"
            "Respond with exactly: "
            '{{"translations": [{{"line_id": "{line_id}", '
            '"text": "<translation>"}}]}}'
        ),
        TranslationResultList,
    ),
    (
        PhaseName.QA,
        "You are a translation quality reviewer. Respond with minimal JSON only.",
        (
            "Review this translation for style violations.\n"
            "Source: {text}\n"
            "Translation: Cherry blossom petals dance "
            "at the school gate on a spring morning.\n"
            "Respond with exactly: "
            '{{"reviews": [{{"line_id": "{line_id}", "violations": []}}]}}'
        ),
        StyleGuideReviewList,
    ),
    (
        PhaseName.EDIT,
        "You are a translation editor. Respond with minimal JSON only.",
        (
            "Edit this translation if needed.\n"
            "Source: {text}\n"
            "Current (line_id: {line_id}): "
            "Cherry blossom petals dance "
            "at the school gate on a spring morning.\n"
            "Respond with exactly: "
            '{{"edited_lines": [{{"line_id": "{line_id}", '
            '"text": "<edited text>"}}], '
            '"changes": []}}'
        ),
        EditOutput,
    ),
]


def validate_output(
    phase: PhaseName,
    output: BaseSchema,
    source_line: SourceLine,
) -> str | None:
    """Validate that a phase output has the correct count and IDs.

    Returns:
        None if valid, an error message string if not.
    """
    if phase == PhaseName.CONTEXT:
        items = output.scene_summaries  # type: ignore[attr-defined]
        if len(items) != 1:
            return f"Expected 1 scene_summary, got {len(items)}"
        if items[0].scene_id != source_line.scene_id:
            return (
                f"Expected scene_id='{source_line.scene_id}', got '{items[0].scene_id}'"
            )
    elif phase == PhaseName.PRETRANSLATION:
        items = output.reviews  # type: ignore[attr-defined]
        if len(items) != 1:
            return f"Expected 1 pretranslation review, got {len(items)}"
        if items[0].line_id != source_line.line_id:
            return f"Expected line_id='{source_line.line_id}', got '{items[0].line_id}'"
    elif phase == PhaseName.TRANSLATE:
        items = output.translations  # type: ignore[attr-defined]
        if len(items) != 1:
            return f"Expected 1 translation, got {len(items)}"
        if items[0].line_id != source_line.line_id:
            return f"Expected line_id='{source_line.line_id}', got '{items[0].line_id}'"
    elif phase == PhaseName.QA:
        items = output.reviews  # type: ignore[attr-defined]
        if len(items) != 1:
            return f"Expected 1 QA review, got {len(items)}"
        if items[0].line_id != source_line.line_id:
            return f"Expected line_id='{source_line.line_id}', got '{items[0].line_id}'"
    elif phase == PhaseName.EDIT:
        items = output.edited_lines  # type: ignore[attr-defined]
        if len(items) != 1:
            return f"Expected 1 edited_line, got {len(items)}"
        if items[0].line_id != source_line.line_id:
            return f"Expected line_id='{source_line.line_id}', got '{items[0].line_id}'"
    return None


async def _run_phase(
    *,
    phase: PhaseName,
    system_prompt: str,
    user_prompt_template: str,
    output_type: type[BaseSchema],
    model: Model,
    model_settings: ModelSettings,
    source_line: SourceLine,
    output_retries: int = 2,
    phase_timeout_s: float | None = None,
) -> PhaseResult:
    """Run a single verification phase against a model.

    Args:
        phase: Pipeline phase being verified.
        system_prompt: System prompt for the agent.
        user_prompt_template: User prompt with {text}/{line_id}.
        output_type: Pydantic schema the agent must produce.
        model: pydantic-ai Model instance.
        model_settings: Model settings for the agent call.
        source_line: Golden input source line.
        output_retries: Pydantic-ai output validation retry limit.
        phase_timeout_s: Wall-clock timeout for the entire phase execution.
            When set, the phase is cancelled if it exceeds this budget and
            a structured FAILED result is returned instead of hanging.

    Returns:
        PhaseResult with pass/fail and error details.
    """
    user_prompt = user_prompt_template.format(
        text=source_line.text,
        line_id=source_line.line_id,
    )
    try:
        agent = Agent(
            model,
            output_type=output_type,
            output_retries=output_retries,
            system_prompt=system_prompt,
        )
        coro = agent.run(user_prompt, model_settings=model_settings)
        if phase_timeout_s is not None:
            result = await asyncio.wait_for(coro, timeout=phase_timeout_s)
        else:
            result = await coro
        output = result.output
        assert isinstance(output, BaseSchema), (
            f"Expected BaseSchema, got {type(output).__name__}"
        )
        error = validate_output(phase, output, source_line)
        if error:
            _log.warning("Phase %s output validation failed: %s", phase, error)
            return PhaseResult(
                phase=phase,
                status=PhaseVerificationStatus.FAILED,
                error_message=(
                    f"Output validation failed: {error}. "
                    "The model produced valid JSON but with incorrect "
                    "count or IDs for the input."
                ),
            )
        return PhaseResult(
            phase=phase,
            status=PhaseVerificationStatus.PASSED,
            error_message=None,
        )
    except TimeoutError:
        _log.warning(
            "Phase %s timed out after %.1fs wall-clock budget",
            phase,
            phase_timeout_s,
        )
        return PhaseResult(
            phase=phase,
            status=PhaseVerificationStatus.FAILED,
            error_message=(
                f"Phase timed out after {phase_timeout_s}s wall-clock budget. "
                "The model did not complete within the allocated time. "
                "Consider increasing timeout_s or max_output_retries in the registry."
            ),
        )
    except Exception as exc:
        _log.warning("Phase %s failed: %s", phase, exc)
        return PhaseResult(
            phase=phase,
            status=PhaseVerificationStatus.FAILED,
            error_message=(
                f"{type(exc).__name__}: {exc}. "
                "Check that the model supports tool-based structured output "
                "and can produce the expected schema."
            ),
        )


async def verify_single_phase(
    *,
    entry: VerifiedModelEntry,
    endpoint: ModelEndpointConfig,
    phase_name: PhaseName,
) -> PhaseResult:
    """Verify a single pipeline phase for one model.

    Designed for per-phase quality tests where each test case runs one
    LLM call, easily fitting within the 45s quality timeout.

    For local models, the caller is responsible for model loading/unloading
    lifecycle management (use ``load_lm_studio_model`` / ``unload_lm_studio_model``
    in fixtures rather than per-test calls).

    Args:
        entry: Registry entry for the model to verify.
        endpoint: Resolved endpoint configuration.
        phase_name: The specific pipeline phase to verify.

    Returns:
        PhaseResult with pass/fail and error details.
    """
    api_key = os.getenv(endpoint.api_key_env) or ""

    # Resolve config overrides
    timeout_s = (
        entry.config_overrides.timeout_s
        if entry.config_overrides.timeout_s is not None
        else endpoint.timeout_s
    )
    temperature = (
        entry.config_overrides.temperature
        if entry.config_overrides.temperature is not None
        else 0.2
    )
    top_p = (
        entry.config_overrides.top_p
        if entry.config_overrides.top_p is not None
        else 1.0
    )
    max_output_tokens = (
        entry.config_overrides.max_output_tokens
        if entry.config_overrides.max_output_tokens is not None
        else _DEFAULT_MAX_OUTPUT_TOKENS
    )
    output_retries = (
        entry.config_overrides.max_output_retries
        if entry.config_overrides.max_output_retries is not None
        else 2
    )
    supports_tool_choice_required = (
        entry.config_overrides.supports_tool_choice_required
        if entry.config_overrides.supports_tool_choice_required is not None
        else True
    )
    max_sdk_retries = entry.config_overrides.max_sdk_retries

    # Wall-clock budget: (1 + output_retries) requests x timeout_s per request
    # Ensures the phase terminates deterministically instead of hanging until
    # pytest kills it.
    phase_timeout_s = (1 + output_retries) * timeout_s

    model, settings = create_model(
        base_url=endpoint.base_url,
        api_key=api_key,
        model_id=entry.model_id,
        temperature=temperature,
        top_p=top_p,
        timeout_s=timeout_s,
        max_output_tokens=max_output_tokens,
        reasoning_effort=entry.config_overrides.reasoning_effort,
        openrouter_provider=endpoint.openrouter_provider,
        strict_tools=endpoint.strict_tools,
        supports_tool_choice_required=supports_tool_choice_required,
        max_retries=max_sdk_retries,
    )

    # Find the matching phase config
    phase_config = None
    for phase, sys_prompt, user_template, output_type in PHASE_CONFIGS:
        if phase == phase_name:
            phase_config = (phase, sys_prompt, user_template, output_type)
            break

    if phase_config is None:
        return PhaseResult(
            phase=phase_name,
            status=PhaseVerificationStatus.FAILED,
            error_message=f"Unknown phase: {phase_name}",
        )

    phase, sys_prompt, user_template, output_type = phase_config
    return await _run_phase(
        phase=phase,
        system_prompt=sys_prompt,
        user_prompt_template=user_template,
        output_type=output_type,
        model=model,
        model_settings=settings,
        source_line=GOLDEN_SOURCE_LINE,
        output_retries=output_retries,
        phase_timeout_s=phase_timeout_s,
    )


async def verify_model(
    *,
    entry: VerifiedModelEntry,
    endpoint: ModelEndpointConfig,
) -> ModelVerificationResult:
    """Verify a single model through the mini 5-phase pipeline.

    For local models, loads the model via LM Studio API first.

    Args:
        entry: Registry entry for the model to verify.
        endpoint: Resolved endpoint configuration.

    Returns:
        ModelVerificationResult with per-phase pass/fail results.
    """
    _log.info("Verifying model %s (%s)", entry.model_id, entry.endpoint_type)

    # Resolve API key (needed for both model loading and inference)
    api_key = os.getenv(endpoint.api_key_env) or ""

    # Track whether we need to unload after verification
    is_local = entry.endpoint_type == "local" and entry.load_endpoint is not None

    # Load timeout is decoupled from per-phase inference timeout
    load_timeout = (
        entry.config_overrides.load_timeout_s
        if entry.config_overrides.load_timeout_s is not None
        else 120.0
    )

    try:
        # Load local model via LM Studio API
        if is_local:
            try:
                await load_lm_studio_model(
                    load_endpoint=entry.load_endpoint,  # type: ignore[arg-type]
                    model_id=entry.model_id,
                    api_key=api_key,
                    timeout_s=load_timeout,
                )
            except ModelLoadError as exc:
                return ModelVerificationResult(
                    model_id=entry.model_id,
                    passed=False,
                    phase_results=[
                        PhaseResult(
                            phase=PhaseName.CONTEXT,
                            status=PhaseVerificationStatus.FAILED,
                            error_message=f"Model loading failed: {exc}",
                        ),
                    ],
                )

        # Apply config overrides — use `is not None` to preserve explicit zeros
        timeout_s = (
            entry.config_overrides.timeout_s
            if entry.config_overrides.timeout_s is not None
            else endpoint.timeout_s
        )
        temperature = (
            entry.config_overrides.temperature
            if entry.config_overrides.temperature is not None
            else 0.2
        )
        top_p = (
            entry.config_overrides.top_p
            if entry.config_overrides.top_p is not None
            else 1.0
        )
        max_output_tokens = (
            entry.config_overrides.max_output_tokens
            if entry.config_overrides.max_output_tokens is not None
            else _DEFAULT_MAX_OUTPUT_TOKENS
        )
        output_retries = (
            entry.config_overrides.max_output_retries
            if entry.config_overrides.max_output_retries is not None
            else 2
        )
        supports_tool_choice_required = (
            entry.config_overrides.supports_tool_choice_required
            if entry.config_overrides.supports_tool_choice_required is not None
            else True
        )
        max_sdk_retries = entry.config_overrides.max_sdk_retries

        # Wall-clock budget per phase (same formula as verify_single_phase)
        phase_timeout_s = (1 + output_retries) * timeout_s

        # Build model via provider factory
        model, settings = create_model(
            base_url=endpoint.base_url,
            api_key=api_key,
            model_id=entry.model_id,
            temperature=temperature,
            top_p=top_p,
            timeout_s=timeout_s,
            max_output_tokens=max_output_tokens,
            reasoning_effort=entry.config_overrides.reasoning_effort,
            openrouter_provider=endpoint.openrouter_provider,
            strict_tools=endpoint.strict_tools,
            supports_tool_choice_required=supports_tool_choice_required,
            max_retries=max_sdk_retries,
        )

        # Run phases sequentially, fail-fast on first failure
        phase_results: list[PhaseResult] = []
        failed = False
        for phase, sys_prompt, user_template, output_type in PHASE_CONFIGS:
            if failed:
                phase_results.append(
                    PhaseResult(
                        phase=phase,
                        status=PhaseVerificationStatus.SKIPPED,
                        error_message="Skipped due to earlier phase failure",
                    )
                )
                continue
            result = await _run_phase(
                phase=phase,
                system_prompt=sys_prompt,
                user_prompt_template=user_template,
                output_type=output_type,
                model=model,
                model_settings=settings,
                source_line=GOLDEN_SOURCE_LINE,
                output_retries=output_retries,
                phase_timeout_s=phase_timeout_s,
            )
            phase_results.append(result)
            if result.status == PhaseVerificationStatus.FAILED:
                failed = True

        all_passed = all(
            r.status == PhaseVerificationStatus.PASSED for r in phase_results
        )

        return ModelVerificationResult(
            model_id=entry.model_id,
            passed=all_passed,
            phase_results=phase_results,
        )
    finally:
        # Always unload local models after verification to free GPU memory
        if is_local:
            try:
                await unload_lm_studio_model(
                    load_endpoint=entry.load_endpoint,
                    model_id=entry.model_id,
                    api_key=api_key,
                    timeout_s=load_timeout,
                )
            except ModelUnloadError:
                _log.warning(
                    "Failed to unload model %s after verification",
                    entry.model_id,
                )


async def verify_registry(
    *,
    registry: VerifiedModelRegistry,
    endpoints: dict[str, ModelEndpointConfig],
    endpoint_filter: str | None = None,
    model_filter: str | None = None,
) -> RegistryVerificationResult:
    """Verify all models in a registry.

    Local models are run sequentially (one model loaded at a time).
    OpenRouter models are also run sequentially for simplicity in the
    verification context — real parallelism is handled by the caller
    if needed.

    Args:
        registry: The verified models registry.
        endpoints: Mapping of endpoint_ref to endpoint configuration.
        endpoint_filter: Optional filter for endpoint type (local/openrouter).
        model_filter: Optional filter for a specific model_id.

    Returns:
        RegistryVerificationResult with per-model results.
    """
    entries = registry.models

    if endpoint_filter is not None:
        entries = [e for e in entries if e.endpoint_type == endpoint_filter]

    if model_filter is not None:
        entries = [e for e in entries if e.model_id == model_filter]

    model_results: list[ModelVerificationResult] = []

    for entry in entries:
        endpoint = endpoints.get(entry.endpoint_ref)
        if endpoint is None:
            model_results.append(
                ModelVerificationResult(
                    model_id=entry.model_id,
                    passed=False,
                    phase_results=[
                        PhaseResult(
                            phase=PhaseName.CONTEXT,
                            status=PhaseVerificationStatus.FAILED,
                            error_message=(
                                "No endpoint configured for "
                                f"endpoint_ref "
                                f"'{entry.endpoint_ref}'. "
                                "Add an endpoint with "
                                "provider_name="
                                f"'{entry.endpoint_ref}' "
                                "to your configuration."
                            ),
                        ),
                    ],
                )
            )
            continue

        result = await verify_model(entry=entry, endpoint=endpoint)
        model_results.append(result)

    all_passed = all(r.passed for r in model_results)

    return RegistryVerificationResult(
        passed=all_passed,
        model_results=model_results,
    )
