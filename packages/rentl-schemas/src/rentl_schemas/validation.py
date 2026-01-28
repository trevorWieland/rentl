"""Validation entrypoints for config and phase schemas."""

from __future__ import annotations

from rentl_schemas.config import PipelineConfig, ProjectConfig, RunConfig
from rentl_schemas.phases import (
    ContextPhaseInput,
    ContextPhaseOutput,
    EditPhaseInput,
    EditPhaseOutput,
    PretranslationPhaseInput,
    PretranslationPhaseOutput,
    QaPhaseInput,
    QaPhaseOutput,
    TranslatePhaseInput,
    TranslatePhaseOutput,
)
from rentl_schemas.primitives import JsonValue
from rentl_schemas.progress import (
    PhaseProgress,
    ProgressMetric,
    ProgressPercentMode,
    ProgressSnapshot,
    ProgressUpdate,
    RunProgress,
)


def validate_project_config(payload: dict[str, JsonValue]) -> ProjectConfig:
    """Validate project configuration payload.

    Args:
        payload: Raw project configuration payload.

    Returns:
        ProjectConfig: Validated project configuration.
    """
    return ProjectConfig.model_validate(payload)


def validate_pipeline_config(payload: dict[str, JsonValue]) -> PipelineConfig:
    """Validate pipeline configuration payload.

    Args:
        payload: Raw pipeline configuration payload.

    Returns:
        PipelineConfig: Validated pipeline configuration.
    """
    return PipelineConfig.model_validate(payload)


def validate_run_config(payload: dict[str, JsonValue]) -> RunConfig:
    """Validate run configuration payload.

    Args:
        payload: Raw run configuration payload.

    Returns:
        RunConfig: Validated run configuration.
    """
    return RunConfig.model_validate(payload, strict=False)


def validate_context_input(payload: dict[str, JsonValue]) -> ContextPhaseInput:
    """Validate context phase input payload.

    Args:
        payload: Raw context phase input payload.

    Returns:
        ContextPhaseInput: Validated context input.
    """
    return ContextPhaseInput.model_validate(payload)


def validate_context_output(payload: dict[str, JsonValue]) -> ContextPhaseOutput:
    """Validate context phase output payload.

    Args:
        payload: Raw context phase output payload.

    Returns:
        ContextPhaseOutput: Validated context output.
    """
    return ContextPhaseOutput.model_validate(payload)


def validate_pretranslation_input(
    payload: dict[str, JsonValue],
) -> PretranslationPhaseInput:
    """Validate pretranslation phase input payload.

    Args:
        payload: Raw source analysis input payload.

    Returns:
        PretranslationPhaseInput: Validated pretranslation input.
    """
    return PretranslationPhaseInput.model_validate(payload)


def validate_pretranslation_output(
    payload: dict[str, JsonValue],
) -> PretranslationPhaseOutput:
    """Validate pretranslation phase output payload.

    Args:
        payload: Raw source analysis output payload.

    Returns:
        PretranslationPhaseOutput: Validated pretranslation output.
    """
    return PretranslationPhaseOutput.model_validate(payload)


def validate_translate_input(payload: dict[str, JsonValue]) -> TranslatePhaseInput:
    """Validate translate phase input payload.

    Args:
        payload: Raw translate phase input payload.

    Returns:
        TranslatePhaseInput: Validated translate input.
    """
    return TranslatePhaseInput.model_validate(payload)


def validate_translate_output(payload: dict[str, JsonValue]) -> TranslatePhaseOutput:
    """Validate translate phase output payload.

    Args:
        payload: Raw translate phase output payload.

    Returns:
        TranslatePhaseOutput: Validated translate output.
    """
    return TranslatePhaseOutput.model_validate(payload)


def validate_qa_input(payload: dict[str, JsonValue]) -> QaPhaseInput:
    """Validate QA phase input payload.

    Args:
        payload: Raw QA phase input payload.

    Returns:
        QaPhaseInput: Validated QA input.
    """
    return QaPhaseInput.model_validate(payload)


def validate_qa_output(payload: dict[str, JsonValue]) -> QaPhaseOutput:
    """Validate QA phase output payload.

    Args:
        payload: Raw QA phase output payload.

    Returns:
        QaPhaseOutput: Validated QA output.
    """
    return QaPhaseOutput.model_validate(payload)


def validate_edit_input(payload: dict[str, JsonValue]) -> EditPhaseInput:
    """Validate edit phase input payload.

    Args:
        payload: Raw edit phase input payload.

    Returns:
        EditPhaseInput: Validated edit input.
    """
    return EditPhaseInput.model_validate(payload)


def validate_edit_output(payload: dict[str, JsonValue]) -> EditPhaseOutput:
    """Validate edit phase output payload.

    Args:
        payload: Raw edit phase output payload.

    Returns:
        EditPhaseOutput: Validated edit output.
    """
    return EditPhaseOutput.model_validate(payload)


def validate_progress_metric(payload: dict[str, JsonValue]) -> ProgressMetric:
    """Validate progress metric payload.

    Args:
        payload: Raw progress metric payload.

    Returns:
        ProgressMetric: Validated progress metric.
    """
    return ProgressMetric.model_validate(payload)


def validate_phase_progress(payload: dict[str, JsonValue]) -> PhaseProgress:
    """Validate phase progress payload.

    Args:
        payload: Raw phase progress payload.

    Returns:
        PhaseProgress: Validated phase progress.
    """
    return PhaseProgress.model_validate(payload)


def validate_run_progress(payload: dict[str, JsonValue]) -> RunProgress:
    """Validate run progress payload.

    Args:
        payload: Raw run progress payload.

    Returns:
        RunProgress: Validated run progress.
    """
    return RunProgress.model_validate(payload)


def validate_progress_snapshot(payload: dict[str, JsonValue]) -> ProgressSnapshot:
    """Validate progress snapshot payload.

    Args:
        payload: Raw progress snapshot payload.

    Returns:
        ProgressSnapshot: Validated progress snapshot.
    """
    return ProgressSnapshot.model_validate(payload)


def validate_progress_update(payload: dict[str, JsonValue]) -> ProgressUpdate:
    """Validate progress update payload.

    Args:
        payload: Raw progress update payload.

    Returns:
        ProgressUpdate: Validated progress update.
    """
    return ProgressUpdate.model_validate(payload)


def validate_progress_monotonic(
    previous: RunProgress,
    current: RunProgress,
) -> None:
    """Validate monotonic progress between two snapshots.

    Args:
        previous: Previous run progress snapshot.
        current: Current run progress snapshot.

    Raises:
        ValueError: If progress regresses for monotonic modes.
    """

    def _should_enforce(mode: ProgressPercentMode) -> bool:
        return mode in {
            ProgressPercentMode.FINAL,
            ProgressPercentMode.LOWER_BOUND,
        }

    def _ensure_percent_monotonic(
        label: str,
        previous_percent: float | None,
        previous_mode: ProgressPercentMode,
        current_percent: float | None,
        current_mode: ProgressPercentMode,
    ) -> None:
        if (
            previous_percent is not None
            and current_percent is not None
            and _should_enforce(previous_mode)
            and _should_enforce(current_mode)
            and current_percent < previous_percent
        ):
            raise ValueError(f"{label} percent regressed")

    _ensure_percent_monotonic(
        "run summary",
        previous.summary.percent_complete,
        previous.summary.percent_mode,
        current.summary.percent_complete,
        current.summary.percent_mode,
    )

    previous_phases = {phase.phase: phase for phase in previous.phases}
    for current_phase in current.phases:
        previous_phase = previous_phases.get(current_phase.phase)
        if previous_phase is None:
            continue
        _ensure_percent_monotonic(
            f"phase {current_phase.phase}",
            previous_phase.summary.percent_complete,
            previous_phase.summary.percent_mode,
            current_phase.summary.percent_complete,
            current_phase.summary.percent_mode,
        )
        previous_metrics = {}
        if previous_phase.metrics:
            previous_metrics = {
                metric.metric_key: metric for metric in previous_phase.metrics
            }
        if not current_phase.metrics:
            continue
        for metric in current_phase.metrics:
            previous_metric = previous_metrics.get(metric.metric_key)
            if previous_metric is None:
                continue
            if metric.completed_units < previous_metric.completed_units:
                raise ValueError(
                    f"metric {metric.metric_key} completed units regressed"
                )
            _ensure_percent_monotonic(
                f"metric {metric.metric_key}",
                previous_metric.percent_complete,
                previous_metric.percent_mode,
                metric.percent_complete,
                metric.percent_mode,
            )
