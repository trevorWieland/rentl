"""Tests for agent telemetry emitter."""

from __future__ import annotations

import asyncio
from uuid import uuid7

from rentl_core.telemetry import AgentTelemetryEmitter
from rentl_io.storage import InMemoryProgressSink
from rentl_schemas.events import ProgressEvent
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import PhaseName
from rentl_schemas.progress import AgentStatus, AgentTelemetry


class _StubLogSink:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    async def emit_log(self, entry: LogEntry) -> None:
        self.entries.append(entry)


def test_agent_telemetry_emitter_writes_sinks() -> None:
    """Telemetry emitter writes progress and log entries."""
    progress_sink = InMemoryProgressSink()
    log_sink = _StubLogSink()
    emitter = AgentTelemetryEmitter(
        progress_sink=progress_sink,
        log_sink=log_sink,
        clock=lambda: "2026-02-03T12:00:00Z",
    )

    update = AgentTelemetry(
        agent_run_id="scene_summarizer_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.COMPLETED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:00:10Z",
        usage=None,
        message="Agent completed",
    )

    asyncio.run(
        emitter.emit(
            run_id=uuid7(),
            event=ProgressEvent.AGENT_COMPLETED,
            update=update,
            timestamp="2026-02-03T12:00:10Z",
        )
    )

    assert len(progress_sink.updates) == 1
    assert progress_sink.updates[0].event == ProgressEvent.AGENT_COMPLETED
    assert len(log_sink.entries) == 1
