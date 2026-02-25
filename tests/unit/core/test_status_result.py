"""Tests for status result aggregation helpers."""

from __future__ import annotations

from uuid import uuid7

import pytest

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


def test_retry_updates_with_same_agent_run_id_counted_separately() -> None:
    """Retries that reuse the same agent_run_id must not lose earlier attempts.

    Regression test: the old dedup keyed only on agent_run_id, so a retry
    (attempt 2) would overwrite the failed attempt 1 entry, silently dropping
    its tokens from the summary totals and waste calculations.
    """
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

    # Attempt 1: FAILED with 100 tokens
    failed_agent = AgentTelemetry(
        agent_run_id="translator_001",
        agent_name="translator",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.FAILED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:00:05Z",
        usage=AgentUsageTotals(
            input_tokens=40,
            output_tokens=60,
            total_tokens=100,
            request_count=1,
            tool_calls=0,
        ),
        message="Agent failed",
    )
    update_failed = ProgressUpdate(
        run_id=run_id,
        event=ProgressEvent.AGENT_FAILED,
        timestamp="2026-02-03T12:00:05Z",
        phase=PhaseName.CONTEXT,
        phase_status=PhaseStatus.RUNNING,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        agent_update=failed_agent,
        message=None,
    )

    # Attempt 2: COMPLETED with 200 tokens (same agent_run_id)
    completed_agent = AgentTelemetry(
        agent_run_id="translator_001",
        agent_name="translator",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.COMPLETED,
        attempt=2,
        started_at="2026-02-03T12:00:10Z",
        completed_at="2026-02-03T12:00:15Z",
        usage=AgentUsageTotals(
            input_tokens=80,
            output_tokens=120,
            total_tokens=200,
            request_count=1,
            tool_calls=0,
        ),
        message="Agent completed",
    )
    update_completed = ProgressUpdate(
        run_id=run_id,
        event=ProgressEvent.AGENT_COMPLETED,
        timestamp="2026-02-03T12:00:15Z",
        phase=PhaseName.CONTEXT,
        phase_status=PhaseStatus.RUNNING,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        agent_update=completed_agent,
        message=None,
    )

    result = build_status_result(
        run_id=run_id,
        run_state=None,
        progress_updates=[update_failed, update_completed],
        log_reference=None,
        progress_file=None,
    )

    assert result.agent_summary is not None
    # Both attempts must be counted (2 entries, not 1)
    assert result.agent_summary.total == 2
    assert result.agent_summary.usage is not None
    # Total tokens = 100 (failed) + 200 (retry) = 300
    assert result.agent_summary.usage.total_tokens == 300
    # Waste includes both failed (100) and retry attempt 2 (200)
    assert result.agent_summary.waste_ratio > 0.0
    # Failed=100, retry=200 → waste=300, total=300 → waste_ratio=1.0
    assert result.agent_summary.waste_ratio == pytest.approx(1.0)
