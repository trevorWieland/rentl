"""Tests for status result aggregation helpers."""

from __future__ import annotations

from uuid import uuid7

from rentl_core.status import build_status_result
from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import PhaseName, PhaseStatus, RunStatus
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    AgentUsageTotals,
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
    ProgressUpdate,
    RunProgress,
)


def test_build_status_result_aggregates_agents() -> None:
    """Status aggregation includes agent telemetry summaries."""
    run_id = uuid7()
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.CONTEXT,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_progress = RunProgress(
        phases=[phase_progress],
        summary=summary,
        phase_weights=None,
    )
    agent_update = AgentTelemetry(
        agent_run_id="scene_summarizer_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.RUNNING,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at=None,
        usage=AgentUsageTotals(
            input_tokens=5,
            output_tokens=7,
            total_tokens=12,
            request_count=1,
            tool_calls=0,
        ),
        message="Agent started",
    )
    update = ProgressUpdate(
        run_id=run_id,
        event=ProgressEvent.AGENT_STARTED,
        timestamp="2026-02-03T12:00:00Z",
        phase=PhaseName.CONTEXT,
        phase_status=PhaseStatus.RUNNING,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        agent_update=agent_update,
        message=None,
    )

    result = build_status_result(
        run_id=run_id,
        run_state=None,
        progress_updates=[update],
        log_reference=None,
        progress_file=None,
    )

    assert result.status == RunStatus.RUNNING
    assert result.current_phase == PhaseName.CONTEXT
    assert result.agent_summary is not None
    assert result.agent_summary.total == 1
    assert result.agent_summary.usage is not None
    assert result.agent_summary.usage.total_tokens == 12
