"""Unit tests for log/progress sink adapters."""

import asyncio
import json
from pathlib import Path
from uuid import UUID

from rentl_core.ports.orchestrator import LogSinkProtocol
from rentl_io.storage import (
    CompositeLogSink,
    CompositeProgressSink,
    FileSystemProgressSink,
    InMemoryProgressSink,
)
from rentl_schemas.events import ProgressEvent
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import LogLevel, PhaseName, PhaseStatus, RunId
from rentl_schemas.progress import (
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
    ProgressUpdate,
    RunProgress,
)


class _StubLogSink(LogSinkProtocol):
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    async def emit_log(self, entry: LogEntry) -> None:
        self.entries.append(entry)


RUN_ID: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb700")


def _build_progress_update() -> ProgressUpdate:
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.TRANSLATE,
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
    return ProgressUpdate(
        run_id=RUN_ID,
        event=ProgressEvent.PHASE_STARTED,
        timestamp="2026-01-26T12:00:00Z",
        phase=PhaseName.TRANSLATE,
        phase_status=PhaseStatus.RUNNING,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        message=None,
    )


def test_in_memory_progress_sink_stores_updates() -> None:
    """In-memory sink records progress updates."""
    sink = InMemoryProgressSink()
    update = _build_progress_update()

    asyncio.run(sink.emit_progress(update))

    assert len(sink.updates) == 1
    assert sink.updates[0].event == ProgressEvent.PHASE_STARTED


def test_composite_progress_sink_forwards_updates() -> None:
    """Composite progress sink forwards to all children."""
    first = InMemoryProgressSink()
    second = InMemoryProgressSink()
    sink = CompositeProgressSink([first, second])
    update = _build_progress_update()

    asyncio.run(sink.emit_progress(update))

    assert len(first.updates) == 1
    assert len(second.updates) == 1


def test_filesystem_progress_sink_appends_jsonl(tmp_path: Path) -> None:
    """Filesystem progress sink appends JSONL entries."""
    path = tmp_path / "progress.jsonl"
    sink = FileSystemProgressSink(str(path))
    update = _build_progress_update()

    asyncio.run(sink.emit_progress(update))

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == ProgressEvent.PHASE_STARTED


def test_composite_log_sink_forwards_entries() -> None:
    """Composite log sink forwards entries to all sinks."""
    first = _StubLogSink()
    second = _StubLogSink()
    sink = CompositeLogSink([first, second])
    entry = LogEntry(
        timestamp="2026-01-26T12:00:01Z",
        level=LogLevel.INFO,
        event="run_started",
        run_id=RUN_ID,
        phase=None,
        message="Run started",
        data=None,
    )

    asyncio.run(sink.emit_log(entry))

    assert len(first.entries) == 1
    assert len(second.entries) == 1
