"""BDD integration tests for end-to-end cost flow in run reports."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

import pytest
from pytest_bdd import given, scenarios, then, when

from rentl.main import (
    _build_run_report_data,  # noqa: PLC2701
    _report_path,  # noqa: PLC2701
    _write_run_report,  # noqa: PLC2701
)
from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import PhaseName, PhaseStatus
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

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.integration

scenarios("../features/cli/report_cost_flow.feature")


def _make_summary() -> tuple[ProgressSummary, PhaseProgress, RunProgress]:
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.CONTEXT,
        status=PhaseStatus.COMPLETED,
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
    return summary, phase_progress, run_progress


def _make_update(
    run_id: UUID,
    agent: AgentTelemetry,
    phase_progress: PhaseProgress,
    run_progress: RunProgress,
) -> ProgressUpdate:
    return ProgressUpdate(
        run_id=run_id,
        event=ProgressEvent.AGENT_COMPLETED
        if agent.status == AgentStatus.COMPLETED
        else ProgressEvent.AGENT_FAILED,
        timestamp="2026-02-03T12:01:00Z",
        phase=PhaseName.CONTEXT,
        phase_status=PhaseStatus.COMPLETED,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        agent_update=agent,
        message=None,
    )


class ReportCostContext:
    """Context object for report cost BDD scenarios."""

    run_id: UUID | None = None
    progress_updates: list[ProgressUpdate] | None = None
    report_data: dict | None = None
    report_path: Path | None = None
    logs_dir: Path | None = None


@given(
    "a workspace with progress data from a mixed-status pipeline with cost",
    target_fixture="ctx",
)
def given_mixed_status_with_cost(tmp_path: Path) -> ReportCostContext:
    """Build progress updates with completed, failed, and retried agents with cost.

    Returns:
        ReportCostContext with mixed-status progress data including cost.
    """
    ctx = ReportCostContext()
    run_id = uuid7()
    ctx.run_id = run_id
    ctx.logs_dir = tmp_path / "logs"

    _, phase_progress, run_progress = _make_summary()

    completed_agent = AgentTelemetry(
        agent_run_id="agent_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.COMPLETED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:01:00Z",
        usage=AgentUsageTotals(
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            request_count=2,
            tool_calls=0,
            cost_usd=0.0060,
        ),
        cost_usd=0.0060,
    )
    failed_agent = AgentTelemetry(
        agent_run_id="agent_002",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.FAILED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:00:30Z",
        usage=AgentUsageTotals(
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
            request_count=1,
            tool_calls=0,
            cost_usd=0.0012,
        ),
        cost_usd=0.0012,
    )
    retried_agent = AgentTelemetry(
        agent_run_id="agent_003",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.COMPLETED,
        attempt=2,
        started_at="2026-02-03T12:01:00Z",
        completed_at="2026-02-03T12:02:00Z",
        usage=AgentUsageTotals(
            input_tokens=400,
            output_tokens=200,
            total_tokens=600,
            request_count=1,
            tool_calls=0,
            cost_usd=0.0024,
        ),
        cost_usd=0.0024,
    )

    ctx.progress_updates = [
        _make_update(run_id, completed_agent, phase_progress, run_progress),
        _make_update(run_id, failed_agent, phase_progress, run_progress),
        _make_update(run_id, retried_agent, phase_progress, run_progress),
    ]
    return ctx


@given(
    "a workspace with progress data from a pipeline without cost",
    target_fixture="ctx",
)
def given_pipeline_without_cost(tmp_path: Path) -> ReportCostContext:
    """Build progress updates with completed agents that have no cost data.

    Returns:
        ReportCostContext with cost-free progress data.
    """
    ctx = ReportCostContext()
    run_id = uuid7()
    ctx.run_id = run_id
    ctx.logs_dir = tmp_path / "logs"

    _, phase_progress, run_progress = _make_summary()

    agent = AgentTelemetry(
        agent_run_id="agent_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.COMPLETED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:01:00Z",
        usage=AgentUsageTotals(
            input_tokens=800,
            output_tokens=400,
            total_tokens=1200,
            request_count=3,
            tool_calls=0,
        ),
    )

    ctx.progress_updates = [
        _make_update(run_id, agent, phase_progress, run_progress),
    ]
    return ctx


@when("I build the run report")
def when_build_report(ctx: ReportCostContext) -> None:
    """Build the run report data and write it to disk."""
    assert ctx.run_id is not None
    assert ctx.progress_updates is not None
    ctx.report_data = _build_run_report_data(
        run_id=ctx.run_id,
        run_state=None,
        progress_updates=ctx.progress_updates,
    )
    assert ctx.logs_dir is not None
    ctx.report_path = _report_path(str(ctx.logs_dir), ctx.run_id)
    _write_run_report(ctx.report_path, ctx.report_data)


# --- Scenario 1: cost data present ---


@then("the report includes total_cost_usd as a positive number")
def then_cost_positive(ctx: ReportCostContext) -> None:
    """Assert total_cost_usd is present and positive."""
    assert ctx.report_data is not None
    assert ctx.report_data["total_cost_usd"] is not None
    assert ctx.report_data["total_cost_usd"] > 0


@then("the report includes cost_by_phase with at least one entry")
def then_cost_by_phase_nonempty(ctx: ReportCostContext) -> None:
    """Assert cost_by_phase contains entries."""
    assert ctx.report_data is not None
    entries = ctx.report_data["cost_by_phase"]
    assert isinstance(entries, list)
    assert len(entries) >= 1
    assert entries[0]["cost_usd"] is not None
    assert entries[0]["cost_usd"] > 0


@then("the report waste_ratio reflects the failed and retried tokens")
def then_waste_ratio_nonzero(ctx: ReportCostContext) -> None:
    """Assert waste_ratio is positive when failed and retried agents exist."""
    assert ctx.report_data is not None
    assert ctx.report_data["waste_ratio"] > 0


@then("the report tokens_failed has positive total_tokens")
def then_tokens_failed_positive(ctx: ReportCostContext) -> None:
    """Assert tokens_failed segment has positive token counts."""
    assert ctx.report_data is not None
    tokens_failed = ctx.report_data["tokens_failed"]
    assert tokens_failed["total_tokens"] > 0
    assert tokens_failed["input_tokens"] > 0
    assert tokens_failed["output_tokens"] > 0


@then("the report tokens_retried has positive total_tokens")
def then_tokens_retried_positive(ctx: ReportCostContext) -> None:
    """Assert tokens_retried segment has positive token counts."""
    assert ctx.report_data is not None
    tokens_retried = ctx.report_data["tokens_retried"]
    assert tokens_retried["total_tokens"] > 0
    assert tokens_retried["input_tokens"] > 0
    assert tokens_retried["output_tokens"] > 0


@then("the report is written to disk as valid JSON")
def then_report_on_disk(ctx: ReportCostContext) -> None:
    """Assert the report file exists on disk and is valid JSON."""
    assert ctx.report_path is not None
    assert ctx.report_path.exists()
    content = ctx.report_path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert parsed["run_id"] == str(ctx.run_id)
    assert "total_cost_usd" in parsed
    assert "waste_ratio" in parsed
    assert "tokens_failed" in parsed
    assert "tokens_retried" in parsed


# --- Scenario 2: no cost data ---


@then("the report has null total_cost_usd")
def then_cost_null(ctx: ReportCostContext) -> None:
    """Assert total_cost_usd is None when no cost data available."""
    assert ctx.report_data is not None
    assert ctx.report_data["total_cost_usd"] is None


@then("the report cost_by_phase entries have null cost")
def then_cost_by_phase_null(ctx: ReportCostContext) -> None:
    """Assert all cost_by_phase entries have null cost."""
    assert ctx.report_data is not None
    entries = ctx.report_data["cost_by_phase"]
    assert isinstance(entries, list)
    for entry in entries:
        assert entry["cost_usd"] is None


@then("the report waste_ratio is 0.0")
def then_waste_ratio_zero(ctx: ReportCostContext) -> None:
    """Assert waste_ratio is zero when all agents completed."""
    assert ctx.report_data is not None
    assert math.isclose(ctx.report_data["waste_ratio"], 0.0, abs_tol=1e-9)


@then("the report tokens_failed has zero total_tokens")
def then_tokens_failed_zero(ctx: ReportCostContext) -> None:
    """Assert tokens_failed segment has zero tokens."""
    assert ctx.report_data is not None
    tokens_failed = ctx.report_data["tokens_failed"]
    assert tokens_failed["total_tokens"] == 0


@then("the report tokens_retried has zero total_tokens")
def then_tokens_retried_zero(ctx: ReportCostContext) -> None:
    """Assert tokens_retried segment has zero tokens."""
    assert ctx.report_data is not None
    tokens_retried = ctx.report_data["tokens_retried"]
    assert tokens_retried["total_tokens"] == 0


# --- Scenario 3: waste ratio correctness ---


@then("the report waste_ratio equals failed plus retried tokens over total tokens")
def then_waste_ratio_exact(ctx: ReportCostContext) -> None:
    """Assert waste_ratio is exactly (failed + retried) / total tokens."""
    assert ctx.report_data is not None
    failed_tokens = ctx.report_data["tokens_failed"]["total_tokens"]
    retried_tokens = ctx.report_data["tokens_retried"]["total_tokens"]
    total_usage = ctx.report_data["token_usage"]
    assert total_usage is not None
    grand_total = total_usage["total_tokens"]
    assert grand_total > 0
    expected = (failed_tokens + retried_tokens) / grand_total
    assert math.isclose(ctx.report_data["waste_ratio"], expected, rel_tol=1e-9)
