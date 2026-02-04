"""Helpers for building status snapshots from run telemetry."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime

from rentl_schemas.events import ProgressEvent
from rentl_schemas.pipeline import RunState
from rentl_schemas.primitives import PhaseName, RunId, RunStatus, Timestamp
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    AgentTelemetrySummary,
    AgentUsageTotals,
    ProgressUpdate,
    RunProgress,
)
from rentl_schemas.responses import RunStatusResult
from rentl_schemas.storage import LogFileReference, StorageReference


def build_status_result(
    *,
    run_id: RunId,
    run_state: RunState | None,
    progress_updates: Sequence[ProgressUpdate],
    log_reference: LogFileReference | None,
    progress_file: StorageReference | None,
) -> RunStatusResult:
    """Build a status snapshot from run state and progress updates.

    Args:
        run_id: Run identifier.
        run_state: Latest run state snapshot if available.
        progress_updates: Progress updates for the run.
        log_reference: Log file reference if available.
        progress_file: Progress JSONL reference if available.

    Returns:
        RunStatusResult: Aggregated status snapshot.
    """
    updated_at = _select_updated_at(run_state, progress_updates)
    status = _select_run_status(run_state, progress_updates)
    current_phase = _select_current_phase(run_state, progress_updates)
    run_progress = _select_run_progress(run_state, progress_updates)
    agents, agent_summary = _aggregate_agents(progress_updates)
    return RunStatusResult(
        run_id=run_id,
        status=status,
        current_phase=current_phase,
        updated_at=updated_at,
        progress=run_progress,
        run_state=run_state,
        agent_summary=agent_summary,
        agents=agents or None,
        log_file=log_reference,
        progress_file=progress_file,
    )


def _select_updated_at(
    run_state: RunState | None,
    updates: Sequence[ProgressUpdate],
) -> Timestamp:
    if updates:
        return updates[-1].timestamp
    if run_state is None:
        return _now_timestamp()
    return (
        run_state.metadata.completed_at
        or run_state.metadata.started_at
        or run_state.metadata.created_at
    )


def _select_run_status(
    run_state: RunState | None,
    updates: Sequence[ProgressUpdate],
) -> RunStatus:
    for update in reversed(updates):
        if update.event == ProgressEvent.RUN_COMPLETED:
            return RunStatus.COMPLETED
        if update.event == ProgressEvent.RUN_FAILED:
            return RunStatus.FAILED
    if run_state is not None:
        return RunStatus(run_state.metadata.status)
    if updates:
        return RunStatus.RUNNING
    return RunStatus.PENDING


def _select_current_phase(
    run_state: RunState | None,
    updates: Sequence[ProgressUpdate],
) -> PhaseName | None:
    if run_state is not None and run_state.metadata.current_phase is not None:
        return PhaseName(run_state.metadata.current_phase)
    for update in reversed(updates):
        if update.phase is not None:
            return PhaseName(update.phase)
    return None


def _select_run_progress(
    run_state: RunState | None,
    updates: Sequence[ProgressUpdate],
) -> RunProgress | None:
    for update in reversed(updates):
        if update.run_progress is not None:
            return update.run_progress
    if run_state is not None:
        return run_state.progress
    return None


def _aggregate_agents(
    updates: Iterable[ProgressUpdate],
) -> tuple[list[AgentTelemetry], AgentTelemetrySummary | None]:
    latest: dict[str, AgentTelemetry] = {}
    for update in updates:
        if update.agent_update is None:
            continue
        latest[update.agent_update.agent_run_id] = update.agent_update
    agents = list(latest.values())
    if not agents:
        return [], None

    by_status: dict[AgentStatus, int] = dict(
        Counter(AgentStatus(agent.status) for agent in agents)
    )
    usage_total: AgentUsageTotals | None = None
    for agent in agents:
        if agent.usage is None:
            continue
        usage_total = _add_usage(usage_total, agent.usage)

    summary = AgentTelemetrySummary(
        total=len(agents),
        by_status=by_status,
        usage=usage_total,
    )
    return agents, summary


def _add_usage(
    total: AgentUsageTotals | None,
    usage: AgentUsageTotals,
) -> AgentUsageTotals:
    if total is None:
        return usage
    return AgentUsageTotals(
        input_tokens=total.input_tokens + usage.input_tokens,
        output_tokens=total.output_tokens + usage.output_tokens,
        total_tokens=total.total_tokens + usage.total_tokens,
        request_count=total.request_count + usage.request_count,
        tool_calls=total.tool_calls + usage.tool_calls,
    )


def _now_timestamp() -> Timestamp:
    value = datetime.now(tz=UTC).isoformat()
    return value.replace("+00:00", "Z")
