"""Unit tests for progress tracking schemas and helpers."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import PhaseName, PhaseStatus, RunId
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    PhaseProgress,
    ProgressMetric,
    ProgressPercentMode,
    ProgressSummary,
    ProgressTotalStatus,
    ProgressUnit,
    ProgressUpdate,
    RunProgress,
    compute_phase_summary,
    compute_run_summary,
)
from rentl_schemas.validation import validate_progress_monotonic

RUN_ID: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")


def build_summary(percent: float | None, mode: ProgressPercentMode) -> ProgressSummary:
    """Build a basic progress summary for tests.

    Returns:
        ProgressSummary: Progress summary instance.
    """
    return ProgressSummary(
        percent_complete=percent,
        percent_mode=mode,
        eta_seconds=None,
        notes=None,
    )


def build_metric(
    completed: int,
    total: int | None,
    total_status: ProgressTotalStatus,
    percent: float | None,
    percent_mode: ProgressPercentMode,
    metric_key: str = "lines_translated",
    unit: ProgressUnit = ProgressUnit.LINES,
) -> ProgressMetric:
    """Build a progress metric for tests.

    Returns:
        ProgressMetric: Progress metric instance.
    """
    return ProgressMetric(
        metric_key=metric_key,
        unit=unit,
        completed_units=completed,
        total_units=total,
        total_status=total_status,
        percent_complete=percent,
        percent_mode=percent_mode,
        eta_seconds=None,
        notes=None,
    )


def test_progress_metric_requires_total_for_percent() -> None:
    """Ensure percent values require totals."""
    with pytest.raises(ValidationError):
        build_metric(
            completed=5,
            total=None,
            total_status=ProgressTotalStatus.UNKNOWN,
            percent=10.0,
            percent_mode=ProgressPercentMode.FINAL,
        )


def test_progress_metric_rejects_completed_over_total() -> None:
    """Ensure completed units cannot exceed totals."""
    with pytest.raises(ValidationError):
        build_metric(
            completed=12,
            total=10,
            total_status=ProgressTotalStatus.LOCKED,
            percent=120.0,
            percent_mode=ProgressPercentMode.FINAL,
        )


def test_progress_metric_allows_discovering_without_total() -> None:
    """Ensure discovery is allowed without totals."""
    metric = build_metric(
        completed=3,
        total=None,
        total_status=ProgressTotalStatus.DISCOVERING,
        percent=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
    )

    assert metric.total_status == ProgressTotalStatus.DISCOVERING


def test_progress_metric_rejects_discovering_with_total() -> None:
    """Ensure discovery status is rejected when totals are known."""
    with pytest.raises(ValidationError):
        build_metric(
            completed=3,
            total=10,
            total_status=ProgressTotalStatus.DISCOVERING,
            percent=None,
            percent_mode=ProgressPercentMode.UNAVAILABLE,
        )


def test_progress_summary_requires_unavailable_when_missing_percent() -> None:
    """Ensure percent mode matches presence of percent values."""
    with pytest.raises(ValidationError):
        ProgressSummary(
            percent_complete=None,
            percent_mode=ProgressPercentMode.FINAL,
            eta_seconds=None,
            notes=None,
        )


def test_progress_update_requires_payload() -> None:
    """Ensure updates include a progress payload."""
    with pytest.raises(ValidationError):
        ProgressUpdate(
            run_id=RUN_ID,
            event=ProgressEvent.PHASE_STARTED,
            timestamp="2026-01-25T12:00:00Z",
            phase=PhaseName.TRANSLATE,
            phase_status=PhaseStatus.RUNNING,
            run_progress=None,
            phase_progress=None,
            metric=None,
            message=None,
        )


def test_progress_update_rejects_phase_mismatch() -> None:
    """Ensure progress updates enforce phase consistency."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=[metric],
        started_at=None,
        completed_at=None,
    )

    with pytest.raises(ValidationError):
        ProgressUpdate(
            run_id=RUN_ID,
            event=ProgressEvent.PHASE_PROGRESS,
            timestamp="2026-01-25T12:00:00Z",
            phase=PhaseName.QA,
            phase_status=PhaseStatus.RUNNING,
            run_progress=None,
            phase_progress=phase_progress,
            metric=None,
            message=None,
        )


def test_progress_update_rejects_phase_status_mismatch() -> None:
    """Ensure progress updates enforce phase status consistency."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.COMPLETED,
        summary=summary,
        metrics=[metric],
        started_at=None,
        completed_at=None,
    )

    with pytest.raises(ValidationError):
        ProgressUpdate(
            run_id=RUN_ID,
            event=ProgressEvent.PHASE_PROGRESS,
            timestamp="2026-01-25T12:00:00Z",
            phase=PhaseName.TRANSLATE,
            phase_status=PhaseStatus.RUNNING,
            run_progress=None,
            phase_progress=phase_progress,
            metric=None,
            message=None,
        )


def test_progress_update_accepts_agent_update() -> None:
    """Ensure agent telemetry updates are accepted."""
    agent_update = AgentTelemetry(
        agent_run_id="scene_summarizer_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.RUNNING,
        attempt=1,
        started_at="2026-01-25T12:00:00Z",
        completed_at=None,
        usage=None,
        message="Agent started",
    )

    update = ProgressUpdate(
        run_id=RUN_ID,
        event=ProgressEvent.AGENT_STARTED,
        timestamp="2026-01-25T12:00:00Z",
        phase=PhaseName.CONTEXT,
        phase_status=None,
        run_progress=None,
        phase_progress=None,
        metric=None,
        agent_update=agent_update,
        message=None,
    )

    assert update.agent_update is not None


def test_phase_weights_must_sum_to_one() -> None:
    """Ensure phase weights sum to 1.0 when provided."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
    )
    phase = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=[metric],
        started_at=None,
        completed_at=None,
    )

    with pytest.raises(ValidationError):
        RunProgress(
            phases=[phase], summary=summary, phase_weights={PhaseName.TRANSLATE: 0.9}
        )


def test_phase_weights_must_cover_phases() -> None:
    """Ensure phase weights cover tracked phases."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
    )
    translate = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=[metric],
        started_at=None,
        completed_at=None,
    )
    qa_metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
        metric_key="lines_checked",
        unit=ProgressUnit.LINES,
    )
    qa = PhaseProgress(
        phase=PhaseName.QA,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=[qa_metric],
        started_at=None,
        completed_at=None,
    )

    with pytest.raises(ValidationError):
        RunProgress(
            phases=[translate, qa],
            summary=summary,
            phase_weights={PhaseName.TRANSLATE: 1.0},
        )


def test_phase_progress_rejects_unknown_metric_key() -> None:
    """Ensure metric keys are validated per phase."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
        metric_key="lines_translated",
    )

    with pytest.raises(ValidationError):
        PhaseProgress(
            phase=PhaseName.QA,
            status=PhaseStatus.RUNNING,
            summary=summary,
            metrics=[metric],
            started_at=None,
            completed_at=None,
        )


def test_phase_progress_rejects_unit_mismatch() -> None:
    """Ensure metric units match phase definitions."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
        metric_key="lines_translated",
        unit=ProgressUnit.SCENES,
    )

    with pytest.raises(ValidationError):
        PhaseProgress(
            phase=PhaseName.TRANSLATE,
            status=PhaseStatus.RUNNING,
            summary=summary,
            metrics=[metric],
            started_at=None,
            completed_at=None,
        )


def test_phase_progress_rejects_duplicate_metric_keys() -> None:
    """Ensure metric keys are unique within a phase."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
        metric_key="lines_translated",
    )

    with pytest.raises(ValidationError):
        PhaseProgress(
            phase=PhaseName.TRANSLATE,
            status=PhaseStatus.RUNNING,
            summary=summary,
            metrics=[metric, metric],
            started_at=None,
            completed_at=None,
        )


def test_progress_update_rejects_phase_not_in_run_progress() -> None:
    """Ensure phase references exist in run progress payloads."""
    summary = build_summary(10.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=[metric],
        started_at=None,
        completed_at=None,
    )
    run_progress = RunProgress(
        phases=[phase_progress],
        summary=summary,
        phase_weights={PhaseName.TRANSLATE: 1.0},
    )

    with pytest.raises(ValidationError):
        ProgressUpdate(
            run_id=RUN_ID,
            event=ProgressEvent.PHASE_PROGRESS,
            timestamp="2026-01-25T12:00:00Z",
            phase=PhaseName.QA,
            phase_status=PhaseStatus.RUNNING,
            run_progress=run_progress,
            phase_progress=None,
            metric=None,
            message=None,
        )


def test_compute_phase_summary_uses_min_percent() -> None:
    """Ensure phase summary uses conservative percent aggregation."""
    metric_low = build_metric(
        completed=20,
        total=100,
        total_status=ProgressTotalStatus.LOCKED,
        percent=20.0,
        percent_mode=ProgressPercentMode.FINAL,
        metric_key="lines_translated",
    )
    metric_high = build_metric(
        completed=80,
        total=100,
        total_status=ProgressTotalStatus.LOCKED,
        percent=80.0,
        percent_mode=ProgressPercentMode.FINAL,
        metric_key="lines_translated",
    )

    summary = compute_phase_summary([metric_low, metric_high])
    assert summary.percent_complete == 20.0
    assert summary.percent_mode == ProgressPercentMode.FINAL


def test_compute_run_summary_defaults_to_equal_weights() -> None:
    """Ensure run summary uses equal weights when none provided."""
    summary_low = build_summary(50.0, ProgressPercentMode.FINAL)
    summary_high = build_summary(100.0, ProgressPercentMode.FINAL)
    metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
    )
    translate = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.RUNNING,
        summary=summary_low,
        metrics=[metric],
        started_at=None,
        completed_at=None,
    )
    qa_metric = build_metric(
        completed=1,
        total=10,
        total_status=ProgressTotalStatus.LOCKED,
        percent=10.0,
        percent_mode=ProgressPercentMode.FINAL,
        metric_key="lines_checked",
        unit=ProgressUnit.LINES,
    )
    qa = PhaseProgress(
        phase=PhaseName.QA,
        status=PhaseStatus.RUNNING,
        summary=summary_high,
        metrics=[qa_metric],
        started_at=None,
        completed_at=None,
    )

    run_summary = compute_run_summary([translate, qa])
    assert run_summary.percent_complete == 75.0


def test_validate_progress_monotonic_raises_on_regression() -> None:
    """Ensure monotonic validator raises on regressions."""
    previous_summary = build_summary(50.0, ProgressPercentMode.FINAL)
    current_summary = build_summary(40.0, ProgressPercentMode.FINAL)
    previous_metric = build_metric(
        completed=50,
        total=100,
        total_status=ProgressTotalStatus.LOCKED,
        percent=50.0,
        percent_mode=ProgressPercentMode.FINAL,
    )
    current_metric = build_metric(
        completed=40,
        total=100,
        total_status=ProgressTotalStatus.LOCKED,
        percent=40.0,
        percent_mode=ProgressPercentMode.FINAL,
    )

    previous_phase = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.RUNNING,
        summary=previous_summary,
        metrics=[previous_metric],
        started_at=None,
        completed_at=None,
    )
    current_phase = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.RUNNING,
        summary=current_summary,
        metrics=[current_metric],
        started_at=None,
        completed_at=None,
    )

    previous = RunProgress(
        phases=[previous_phase],
        summary=previous_summary,
        phase_weights={PhaseName.TRANSLATE: 1.0},
    )
    current = RunProgress(
        phases=[current_phase],
        summary=current_summary,
        phase_weights={PhaseName.TRANSLATE: 1.0},
    )

    with pytest.raises(ValueError):
        validate_progress_monotonic(previous, current)
