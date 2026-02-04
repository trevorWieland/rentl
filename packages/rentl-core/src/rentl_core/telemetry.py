"""Emit structured agent telemetry to log and progress sinks."""

from __future__ import annotations

from collections.abc import Callable

from rentl_core.ports.orchestrator import LogSinkProtocol, ProgressSinkProtocol
from rentl_schemas.events import AgentEvent, ProgressEvent
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import LogLevel, PhaseName, RunId, Timestamp
from rentl_schemas.progress import AgentStatus, AgentTelemetry, ProgressUpdate


class AgentTelemetryEmitter:
    """Emit agent telemetry updates to progress/log sinks."""

    def __init__(
        self,
        *,
        progress_sink: ProgressSinkProtocol | None,
        log_sink: LogSinkProtocol | None,
        clock: Callable[[], Timestamp],
    ) -> None:
        """Initialize the telemetry emitter.

        Args:
            progress_sink: Optional progress sink for agent updates.
            log_sink: Optional log sink for agent updates.
            clock: Timestamp provider for telemetry events.
        """
        self._progress_sink = progress_sink
        self._log_sink = log_sink
        self._clock = clock

    async def emit(
        self,
        *,
        run_id: RunId,
        event: ProgressEvent,
        update: AgentTelemetry,
        timestamp: Timestamp | None = None,
        message: str | None = None,
    ) -> None:
        """Emit agent telemetry to configured sinks."""
        payload_timestamp = timestamp or self._clock()
        payload_message = message or update.message

        if self._progress_sink is not None:
            progress_update = ProgressUpdate(
                run_id=run_id,
                event=event,
                timestamp=payload_timestamp,
                phase=PhaseName(update.phase),
                phase_status=None,
                run_progress=None,
                phase_progress=None,
                metric=None,
                agent_update=update,
                message=payload_message,
            )
            await self._progress_sink.emit_progress(progress_update)

        if self._log_sink is not None:
            log_event = _agent_event_from_progress(event)
            log_level = (
                LogLevel.ERROR if update.status == AgentStatus.FAILED else LogLevel.INFO
            )
            log_entry = LogEntry(
                timestamp=payload_timestamp,
                level=log_level,
                event=log_event,
                run_id=run_id,
                phase=PhaseName(update.phase),
                message=payload_message or _default_message(update.status),
                data=update.model_dump(exclude_none=True),
            )
            await self._log_sink.emit_log(log_entry)


def _agent_event_from_progress(event: ProgressEvent) -> AgentEvent:
    if event == ProgressEvent.AGENT_STARTED:
        return AgentEvent.STARTED
    if event == ProgressEvent.AGENT_PROGRESS:
        return AgentEvent.PROGRESS
    if event == ProgressEvent.AGENT_COMPLETED:
        return AgentEvent.COMPLETED
    if event == ProgressEvent.AGENT_FAILED:
        return AgentEvent.FAILED
    return AgentEvent.PROGRESS


def _default_message(status: AgentStatus) -> str:
    if status == AgentStatus.COMPLETED:
        return "Agent completed"
    if status == AgentStatus.FAILED:
        return "Agent failed"
    return "Agent running"
