"""Unit tests for progress tracking schemas and helpers."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import PhaseName, PhaseStatus, RunId, RunStatus
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    AgentUsageTotals,
    OutputValidationDiagnostic,
    PhaseProgress,
    ProgressMetric,
    ProgressPercentMode,
    ProgressSnapshot,
    ProgressSummary,
    ProgressTotalStatus,
    ProgressUnit,
    ProgressUpdate,
    RunProgress,
    SegmentedUsageTotals,
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
    assert summary.percent_complete == pytest.approx(20.0)
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
    assert run_summary.percent_complete == pytest.approx(75.0)


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


def test_agent_telemetry_coerces_phase_string() -> None:
    """Ensure AgentTelemetry coerces phase string to PhaseName."""
    telemetry = AgentTelemetry(
        agent_run_id="test_run_001",
        agent_name="scene_summarizer",
        phase="context",  # type: ignore[arg-type]
        status=AgentStatus.RUNNING,
    )
    assert telemetry.phase == PhaseName.CONTEXT


def test_phase_progress_coerces_phase_string() -> None:
    """Ensure PhaseProgress coerces phase string to PhaseName."""
    progress = PhaseProgress(
        phase="translate",  # type: ignore[arg-type]
        status=PhaseStatus.PENDING,
        summary=build_summary(None, ProgressPercentMode.UNAVAILABLE),
    )
    assert progress.phase == PhaseName.TRANSLATE


def test_progress_snapshot_coerces_current_phase_string() -> None:
    """Ensure ProgressSnapshot coerces current_phase string to PhaseName."""
    snapshot = ProgressSnapshot(
        run_id=RUN_ID,
        status=RunStatus.PENDING,
        current_phase="qa",  # type: ignore[arg-type]
        progress=RunProgress(
            phases=[
                PhaseProgress(
                    phase=PhaseName.QA,
                    status=PhaseStatus.PENDING,
                    summary=build_summary(None, ProgressPercentMode.UNAVAILABLE),
                )
            ],
            summary=build_summary(None, ProgressPercentMode.UNAVAILABLE),
        ),
        updated_at="2026-01-26T00:00:00Z",
    )
    assert snapshot.current_phase == PhaseName.QA


def test_progress_update_coerces_phase_string() -> None:
    """Ensure ProgressUpdate coerces phase string to PhaseName."""
    update = ProgressUpdate(
        run_id=RUN_ID,
        event=ProgressEvent.PHASE_STARTED,
        timestamp="2026-01-26T00:00:00Z",
        phase="translate",  # type: ignore[arg-type]
        run_progress=RunProgress(
            phases=[
                PhaseProgress(
                    phase=PhaseName.TRANSLATE,
                    status=PhaseStatus.RUNNING,
                    summary=build_summary(None, ProgressPercentMode.UNAVAILABLE),
                )
            ],
            summary=build_summary(None, ProgressPercentMode.UNAVAILABLE),
        ),
    )
    assert update.phase == PhaseName.TRANSLATE


def test_output_validation_diagnostic_roundtrip() -> None:
    """OutputValidationDiagnostic serializes and deserializes correctly."""
    diag = OutputValidationDiagnostic(
        retry_index=3,
        model_output='{"reviews": []}',
        validation_errors=[
            "('reviews',): List should have at least 1 item [too_short]"
        ],
    )
    json_str = diag.model_dump_json()
    restored = OutputValidationDiagnostic.model_validate_json(json_str)
    assert restored.retry_index == 3
    assert restored.model_output == '{"reviews": []}'
    assert restored.validation_errors == diag.validation_errors


def test_output_validation_diagnostic_minimal() -> None:
    """OutputValidationDiagnostic accepts None for optional fields."""
    diag = OutputValidationDiagnostic(
        retry_index=1,
        model_output=None,
        validation_errors=None,
    )
    assert diag.retry_index == 1
    assert diag.model_output is None
    assert diag.validation_errors is None


def test_agent_telemetry_with_diagnostics_roundtrip() -> None:
    """AgentTelemetry with diagnostics serializes and deserializes correctly."""
    diagnostics = [
        OutputValidationDiagnostic(
            retry_index=1,
            model_output='{"bad": "data"}',
            validation_errors=["field required"],
        ),
        OutputValidationDiagnostic(
            retry_index=2,
            model_output=None,
            validation_errors=["Plain text response when structured output expected"],
        ),
    ]
    telemetry = AgentTelemetry(
        agent_run_id="test_run_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        status=AgentStatus.FAILED,
        diagnostics=diagnostics,
        message="Agent produced invalid output",
    )
    json_str = telemetry.model_dump_json()
    restored = AgentTelemetry.model_validate_json(json_str)
    assert restored.diagnostics is not None
    assert len(restored.diagnostics) == 2
    assert restored.diagnostics[0].retry_index == 1
    assert restored.diagnostics[1].model_output is None


def test_agent_telemetry_without_diagnostics() -> None:
    """AgentTelemetry defaults diagnostics to None."""
    telemetry = AgentTelemetry(
        agent_run_id="test_run_002",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        status=AgentStatus.COMPLETED,
    )
    assert telemetry.diagnostics is None


# --- SegmentedUsageTotals tests ---


def test_segmented_usage_totals_defaults() -> None:
    """SegmentedUsageTotals initializes with zero-value defaults."""
    segmented = SegmentedUsageTotals()
    assert segmented.completed.total_tokens == 0
    assert segmented.failed.total_tokens == 0
    assert segmented.retry.total_tokens == 0


def test_segmented_usage_totals_with_values() -> None:
    """SegmentedUsageTotals accepts explicit usage values per segment."""
    segmented = SegmentedUsageTotals(
        completed=AgentUsageTotals(
            input_tokens=100, output_tokens=200, total_tokens=300
        ),
        failed=AgentUsageTotals(input_tokens=10, output_tokens=20, total_tokens=30),
        retry=AgentUsageTotals(input_tokens=5, output_tokens=10, total_tokens=15),
    )
    assert segmented.completed.input_tokens == 100
    assert segmented.failed.total_tokens == 30
    assert segmented.retry.output_tokens == 10


def test_segmented_usage_totals_roundtrip() -> None:
    """SegmentedUsageTotals serializes and deserializes correctly."""
    segmented = SegmentedUsageTotals(
        completed=AgentUsageTotals(
            input_tokens=500,
            output_tokens=1000,
            total_tokens=1500,
            request_count=5,
            tool_calls=3,
            cost_usd=0.05,
        ),
        failed=AgentUsageTotals(
            input_tokens=50, output_tokens=100, total_tokens=150, cost_usd=0.005
        ),
        retry=AgentUsageTotals(input_tokens=25, output_tokens=50, total_tokens=75),
    )
    json_str = segmented.model_dump_json()
    restored = SegmentedUsageTotals.model_validate_json(json_str)
    assert restored.completed.total_tokens == 1500
    assert restored.completed.cost_usd == pytest.approx(0.05)
    assert restored.failed.cost_usd == pytest.approx(0.005)
    assert restored.retry.cost_usd is None


# --- AgentUsageTotals cost_usd tests ---


def test_agent_usage_totals_cost_usd_defaults_none() -> None:
    """AgentUsageTotals.cost_usd defaults to None."""
    usage = AgentUsageTotals(input_tokens=10, output_tokens=20, total_tokens=30)
    assert usage.cost_usd is None


def test_agent_usage_totals_cost_usd_accepts_value() -> None:
    """AgentUsageTotals accepts cost_usd when provided."""
    usage = AgentUsageTotals(
        input_tokens=10, output_tokens=20, total_tokens=30, cost_usd=0.0123
    )
    assert usage.cost_usd == pytest.approx(0.0123)


def test_agent_usage_totals_rejects_negative_cost() -> None:
    """AgentUsageTotals rejects negative cost_usd."""
    with pytest.raises(ValidationError):
        AgentUsageTotals(
            input_tokens=10, output_tokens=20, total_tokens=30, cost_usd=-0.01
        )


def test_agent_usage_totals_cost_usd_roundtrip() -> None:
    """AgentUsageTotals with cost_usd serializes and deserializes correctly."""
    usage = AgentUsageTotals(
        input_tokens=100,
        output_tokens=200,
        total_tokens=300,
        request_count=2,
        tool_calls=1,
        cost_usd=0.042,
    )
    json_str = usage.model_dump_json()
    restored = AgentUsageTotals.model_validate_json(json_str)
    assert restored.cost_usd == pytest.approx(0.042)
    assert restored.total_tokens == 300


# --- AgentTelemetry cost_usd tests ---


def test_agent_telemetry_cost_usd_defaults_none() -> None:
    """AgentTelemetry.cost_usd defaults to None."""
    telemetry = AgentTelemetry(
        agent_run_id="cost_test_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        status=AgentStatus.COMPLETED,
    )
    assert telemetry.cost_usd is None


def test_agent_telemetry_cost_usd_accepts_value() -> None:
    """AgentTelemetry accepts cost_usd from OpenRouter or config."""
    telemetry = AgentTelemetry(
        agent_run_id="cost_test_002",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        status=AgentStatus.COMPLETED,
        cost_usd=0.0567,
        usage=AgentUsageTotals(
            input_tokens=100, output_tokens=200, total_tokens=300, cost_usd=0.0567
        ),
    )
    assert telemetry.cost_usd == pytest.approx(0.0567)
    assert telemetry.usage is not None
    assert telemetry.usage.cost_usd == pytest.approx(0.0567)


def test_agent_telemetry_cost_usd_roundtrip() -> None:
    """AgentTelemetry with cost_usd serializes and deserializes correctly."""
    telemetry = AgentTelemetry(
        agent_run_id="cost_test_003",
        agent_name="translator",
        phase=PhaseName.TRANSLATE,
        status=AgentStatus.COMPLETED,
        cost_usd=0.123,
        usage=AgentUsageTotals(
            input_tokens=1000,
            output_tokens=2000,
            total_tokens=3000,
            request_count=3,
            tool_calls=2,
            cost_usd=0.123,
        ),
    )
    json_str = telemetry.model_dump_json()
    restored = AgentTelemetry.model_validate_json(json_str)
    assert restored.cost_usd == pytest.approx(0.123)
    assert restored.usage is not None
    assert restored.usage.cost_usd == pytest.approx(0.123)


def test_agent_telemetry_rejects_negative_cost() -> None:
    """AgentTelemetry rejects negative cost_usd."""
    with pytest.raises(ValidationError):
        AgentTelemetry(
            agent_run_id="cost_test_004",
            agent_name="scene_summarizer",
            phase=PhaseName.CONTEXT,
            status=AgentStatus.COMPLETED,
            cost_usd=-0.01,
        )


def test_segmented_usage_totals_mixed_cost_availability() -> None:
    """SegmentedUsageTotals handles mixed cost availability gracefully."""
    segmented = SegmentedUsageTotals(
        completed=AgentUsageTotals(
            input_tokens=100, output_tokens=200, total_tokens=300, cost_usd=0.05
        ),
        failed=AgentUsageTotals(
            input_tokens=10, output_tokens=20, total_tokens=30, cost_usd=None
        ),
        retry=AgentUsageTotals(
            input_tokens=5, output_tokens=10, total_tokens=15, cost_usd=None
        ),
    )
    assert segmented.completed.cost_usd == pytest.approx(0.05)
    assert segmented.failed.cost_usd is None
    assert segmented.retry.cost_usd is None
