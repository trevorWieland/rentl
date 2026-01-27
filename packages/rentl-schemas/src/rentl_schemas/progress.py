"""Progress tracking schemas for pipeline phases and runs."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import (
    EVENT_NAME_PATTERN,
    PhaseName,
    PhaseStatus,
    RunId,
    RunStatus,
    Timestamp,
)

type ProgressMetricKey = Annotated[str, Field(pattern=EVENT_NAME_PATTERN)]


class ProgressUnit(StrEnum):
    """Units used for progress tracking metrics."""

    LINES = "lines"
    SCENES = "scenes"
    CHARACTERS = "characters"
    ISSUES = "issues"
    EDITS = "edits"


PHASE_METRIC_DEFINITIONS: dict[PhaseName, dict[ProgressMetricKey, ProgressUnit]] = {
    PhaseName.INGEST: {},
    PhaseName.CONTEXT: {
        "scenes_summarized": ProgressUnit.SCENES,
        "characters_profiled": ProgressUnit.CHARACTERS,
    },
    PhaseName.PRETRANSLATION: {
        "lines_annotated": ProgressUnit.LINES,
    },
    PhaseName.TRANSLATE: {
        "lines_translated": ProgressUnit.LINES,
    },
    PhaseName.QA: {
        "lines_checked": ProgressUnit.LINES,
        "issues_found": ProgressUnit.ISSUES,
        "issues_resolved": ProgressUnit.ISSUES,
    },
    PhaseName.EDIT: {
        "lines_edited": ProgressUnit.EDITS,
        "issues_resolved": ProgressUnit.ISSUES,
    },
    PhaseName.EXPORT: {},
}


class ProgressTotalStatus(StrEnum):
    """Status for total unit counts used in progress reporting."""

    UNKNOWN = "unknown"
    DISCOVERING = "discovering"
    ESTIMATED = "estimated"
    LOCKED = "locked"


class ProgressPercentMode(StrEnum):
    """Mode describing how a percent value should be interpreted."""

    UNAVAILABLE = "unavailable"
    LOWER_BOUND = "lower_bound"
    ESTIMATED = "estimated"
    FINAL = "final"


class ProgressSummary(BaseSchema):
    """Summary progress information for a phase or run."""

    percent_complete: float | None = Field(
        None, ge=0, le=100, description="Percent complete when reportable"
    )
    percent_mode: ProgressPercentMode = Field(..., description="Percent reporting mode")
    eta_seconds: float | None = Field(
        None, ge=0, description="Estimated seconds remaining"
    )
    notes: str | None = Field(
        None, description="Optional context for progress reporting"
    )

    @model_validator(mode="after")
    def _validate_percent_mode(self) -> ProgressSummary:
        if self.percent_complete is None:
            if self.percent_mode != ProgressPercentMode.UNAVAILABLE:
                raise ValueError(
                    "percent_mode must be unavailable when percent_complete is None"
                )
        elif self.percent_mode == ProgressPercentMode.UNAVAILABLE:
            raise ValueError(
                "percent_mode cannot be unavailable when percent_complete is set"
            )
        return self


class ProgressMetric(BaseSchema):
    """Metric-level progress tracking information."""

    metric_key: ProgressMetricKey = Field(
        ..., description="Metric identifier in snake_case"
    )
    unit: ProgressUnit = Field(..., description="Metric unit type")
    completed_units: int = Field(..., ge=0, description="Completed unit count")
    total_units: int | None = Field(
        None, ge=0, description="Total unit count when known"
    )
    total_status: ProgressTotalStatus = Field(..., description="Total unit status")
    percent_complete: float | None = Field(
        None, ge=0, le=100, description="Percent complete when reportable"
    )
    percent_mode: ProgressPercentMode = Field(..., description="Percent reporting mode")
    eta_seconds: float | None = Field(
        None, ge=0, description="Estimated seconds remaining"
    )
    notes: str | None = Field(None, description="Optional context for the metric")

    @model_validator(mode="after")
    def _validate_metric(self) -> ProgressMetric:
        if self.total_units is None:
            if self.total_status not in {
                ProgressTotalStatus.UNKNOWN,
                ProgressTotalStatus.DISCOVERING,
            }:
                raise ValueError(
                    "total_status must be unknown or discovering when total_units is "
                    "None"
                )
            if self.percent_complete is not None:
                raise ValueError("percent_complete requires total_units")
            if self.percent_mode != ProgressPercentMode.UNAVAILABLE:
                raise ValueError(
                    "percent_mode must be unavailable when total_units is None"
                )
        else:
            if self.total_status in {
                ProgressTotalStatus.UNKNOWN,
                ProgressTotalStatus.DISCOVERING,
            }:
                raise ValueError(
                    "total_status cannot be unknown or discovering when total_units is "
                    "set"
                )
            if self.completed_units > self.total_units:
                raise ValueError("completed_units cannot exceed total_units")

        if self.percent_complete is None:
            if self.percent_mode != ProgressPercentMode.UNAVAILABLE:
                raise ValueError(
                    "percent_mode must be unavailable when percent_complete is None"
                )
        else:
            if self.percent_mode == ProgressPercentMode.UNAVAILABLE:
                raise ValueError(
                    "percent_mode cannot be unavailable when percent_complete is set"
                )
            if (
                self.percent_mode == ProgressPercentMode.FINAL
                and self.total_status != ProgressTotalStatus.LOCKED
            ):
                raise ValueError("percent_mode final requires total_status locked")
            if (
                self.percent_mode == ProgressPercentMode.ESTIMATED
                and self.total_status != ProgressTotalStatus.ESTIMATED
            ):
                raise ValueError(
                    "percent_mode estimated requires total_status estimated"
                )
            if (
                self.percent_mode == ProgressPercentMode.LOWER_BOUND
                and self.total_status != ProgressTotalStatus.ESTIMATED
            ):
                raise ValueError(
                    "percent_mode lower_bound requires total_status estimated"
                )
        return self


class PhaseProgress(BaseSchema):
    """Progress tracking for a single pipeline phase."""

    phase: PhaseName = Field(..., description="Phase name")
    status: PhaseStatus = Field(..., description="Phase status")
    summary: ProgressSummary = Field(..., description="Summary progress for the phase")
    metrics: list[ProgressMetric] | None = Field(
        None, description="Metric breakdown for the phase"
    )
    started_at: Timestamp | None = Field(None, description="Phase start timestamp")
    completed_at: Timestamp | None = Field(
        None, description="Phase completion timestamp"
    )

    @model_validator(mode="after")
    def _validate_metrics(self) -> PhaseProgress:
        if self.metrics is None:
            return self
        allowed = PHASE_METRIC_DEFINITIONS.get(self.phase)
        if allowed is None:
            raise ValueError("metrics are not defined for this phase")
        if not allowed and self.metrics:
            raise ValueError("metrics are not allowed for this phase")
        seen_keys: set[str] = set()
        for metric in self.metrics:
            if metric.metric_key in seen_keys:
                raise ValueError("metric_key values must be unique per phase")
            seen_keys.add(metric.metric_key)
            expected_unit = allowed.get(metric.metric_key)
            if expected_unit is None:
                raise ValueError("metric_key is not allowed for this phase")
            if metric.unit != expected_unit:
                raise ValueError("metric unit does not match phase definition")
        return self


class RunProgress(BaseSchema):
    """Overall run progress across all phases."""

    phases: list[PhaseProgress] = Field(
        ..., min_length=1, description="Phase progress list"
    )
    summary: ProgressSummary = Field(..., description="Summary progress for the run")
    phase_weights: dict[PhaseName, float] | None = Field(
        None, description="Optional phase weights used for aggregation"
    )

    @model_validator(mode="after")
    def _validate_phase_weights(self) -> RunProgress:
        seen_phases = {phase.phase for phase in self.phases}
        if len(seen_phases) != len(self.phases):
            raise ValueError("phase entries must be unique")
        if self.phase_weights:
            total_weight = 0.0
            weight_phases = set(self.phase_weights.keys())
            if weight_phases != seen_phases:
                raise ValueError("phase_weights must cover tracked phases")
            for weight in self.phase_weights.values():
                if weight <= 0:
                    raise ValueError("phase_weights must be positive")
                total_weight += weight
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError("phase_weights must sum to 1.0")
        return self


class ProgressSnapshot(BaseSchema):
    """Snapshot of run progress for CLI or API responses."""

    run_id: RunId = Field(..., description="Run identifier")
    status: RunStatus = Field(..., description="Overall run status")
    current_phase: PhaseName | None = Field(None, description="Current running phase")
    progress: RunProgress = Field(..., description="Run progress snapshot")
    updated_at: Timestamp = Field(..., description="Snapshot timestamp")
    message: str | None = Field(None, description="Optional progress message")


class ProgressUpdate(BaseSchema):
    """Incremental progress update suitable for logs or streaming."""

    run_id: RunId = Field(..., description="Run identifier")
    event: ProgressEvent = Field(..., description="Progress event name in snake_case")
    timestamp: Timestamp = Field(..., description="Update timestamp")
    phase: PhaseName | None = Field(None, description="Associated phase")
    phase_status: PhaseStatus | None = Field(
        None, description="Phase status for this update"
    )
    run_progress: RunProgress | None = Field(
        None, description="Optional run progress payload"
    )
    phase_progress: PhaseProgress | None = Field(
        None, description="Optional phase progress payload"
    )
    metric: ProgressMetric | None = Field(
        None, description="Optional metric update payload"
    )
    message: str | None = Field(None, description="Optional progress message")

    @model_validator(mode="after")
    def _validate_payload(self) -> ProgressUpdate:
        if not (self.run_progress or self.phase_progress or self.metric):
            raise ValueError(
                "progress update must include run_progress, phase_progress, or metric"
            )
        if self.phase is None and (self.phase_progress or self.metric):
            raise ValueError("phase is required when phase progress is provided")
        if self.phase_status is not None and self.phase is None:
            raise ValueError("phase is required when phase_status is provided")
        if self.phase_progress and self.phase != self.phase_progress.phase:
            raise ValueError("phase does not match phase_progress.phase")
        if (
            self.phase_progress
            and self.phase_status is not None
            and self.phase_status != self.phase_progress.status
        ):
            raise ValueError("phase_status does not match phase_progress.status")
        if (
            self.run_progress
            and self.phase is not None
            and not any(phase.phase == self.phase for phase in self.run_progress.phases)
        ):
            raise ValueError("phase is not present in run_progress phases")
        return self


def _select_percent_mode(
    modes: list[ProgressPercentMode | str],
) -> ProgressPercentMode:
    """Select the least confident percent mode from a list.

    Returns:
        ProgressPercentMode: Least confident percent mode.
    """
    if not modes:
        return ProgressPercentMode.UNAVAILABLE
    normalized = [
        mode if isinstance(mode, ProgressPercentMode) else ProgressPercentMode(mode)
        for mode in modes
    ]
    order = {
        ProgressPercentMode.UNAVAILABLE: 0,
        ProgressPercentMode.LOWER_BOUND: 1,
        ProgressPercentMode.ESTIMATED: 2,
        ProgressPercentMode.FINAL: 3,
    }
    return min(normalized, key=lambda mode: order[mode])


def compute_phase_summary(
    metrics: list[ProgressMetric] | None,
    eta_seconds: float | None = None,
    notes: str | None = None,
) -> ProgressSummary:
    """Compute a summary progress value from phase metrics.

    Returns:
        ProgressSummary: Summary progress for the phase.
    """
    if not metrics:
        return ProgressSummary(
            percent_complete=None,
            percent_mode=ProgressPercentMode.UNAVAILABLE,
            eta_seconds=eta_seconds,
            notes=notes,
        )

    percents = [metric.percent_complete for metric in metrics]
    if any(percent is None for percent in percents):
        return ProgressSummary(
            percent_complete=None,
            percent_mode=ProgressPercentMode.UNAVAILABLE,
            eta_seconds=eta_seconds,
            notes=notes,
        )

    percent_complete = min(percent for percent in percents if percent is not None)
    percent_mode = _select_percent_mode([metric.percent_mode for metric in metrics])
    if eta_seconds is None:
        eta_values = [metric.eta_seconds for metric in metrics]
        if all(value is not None for value in eta_values):
            eta_seconds = max(value for value in eta_values if value is not None)

    return ProgressSummary(
        percent_complete=percent_complete,
        percent_mode=percent_mode,
        eta_seconds=eta_seconds,
        notes=notes,
    )


def compute_run_summary(
    phases: list[PhaseProgress],
    phase_weights: dict[PhaseName, float] | None = None,
    eta_seconds: float | None = None,
    notes: str | None = None,
) -> ProgressSummary:
    """Compute a run summary progress value from phase summaries.

    Raises:
        ValueError: If phase entries are not unique or weights are invalid.

    Returns:
        ProgressSummary: Summary progress for the run.
    """
    if not phases:
        return ProgressSummary(
            percent_complete=None,
            percent_mode=ProgressPercentMode.UNAVAILABLE,
            eta_seconds=eta_seconds,
            notes=notes,
        )

    seen_phases = {phase.phase for phase in phases}
    if len(seen_phases) != len(phases):
        raise ValueError("phase entries must be unique")

    if phase_weights is None:
        weight_value = 1.0 / len(phases)
        phase_weights = {phase.phase: weight_value for phase in phases}
    else:
        weight_phases = set(phase_weights.keys())
        if weight_phases != seen_phases:
            raise ValueError("phase_weights must cover tracked phases")
        total_weight = sum(phase_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError("phase_weights must sum to 1.0")

    percents = [phase.summary.percent_complete for phase in phases]
    if any(percent is None for percent in percents):
        return ProgressSummary(
            percent_complete=None,
            percent_mode=ProgressPercentMode.UNAVAILABLE,
            eta_seconds=eta_seconds,
            notes=notes,
        )

    percent_complete = 0.0
    for phase in phases:
        percent_complete += phase_weights[phase.phase] * (
            phase.summary.percent_complete or 0.0
        )

    percent_mode = _select_percent_mode([
        phase.summary.percent_mode for phase in phases
    ])

    if eta_seconds is None:
        eta_values = [phase.summary.eta_seconds for phase in phases]
        if all(value is not None for value in eta_values):
            eta_seconds = sum(value for value in eta_values if value is not None)

    return ProgressSummary(
        percent_complete=percent_complete,
        percent_mode=percent_mode,
        eta_seconds=eta_seconds,
        notes=notes,
    )
