"""Unit tests for log/progress sink adapters."""

import asyncio
import io
import json
from pathlib import Path
from uuid import UUID

from rentl_core.ports.orchestrator import LogSinkProtocol
from rentl_io.storage import (
    CompositeLogSink,
    CompositeProgressSink,
    ConsoleLogSink,
    FileSystemProgressSink,
    InMemoryProgressSink,
    NoopLogSink,
    build_log_sink,
)
from rentl_io.storage.filesystem import FileSystemLogStore
from rentl_schemas.config import LoggingConfig, LogSinkConfig
from rentl_schemas.events import ProgressEvent
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import (
    LogLevel,
    LogSinkType,
    PhaseName,
    PhaseStatus,
    RunId,
)
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


def test_console_log_sink_writes_jsonl() -> None:
    """Console sink writes JSONL entries to the stream."""
    stream = io.StringIO()
    sink = ConsoleLogSink(stream=stream)
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

    output = stream.getvalue().strip()
    payload = json.loads(output)
    assert payload["event"] == "run_started"


def test_noop_log_sink_drops_entries() -> None:
    """Noop sink ignores entries without error."""
    sink = NoopLogSink()
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


def test_build_log_sink_supports_multiple_types(tmp_path: Path) -> None:
    """build_log_sink returns a composite when multiple sinks are configured."""
    log_store = FileSystemLogStore(logs_dir=str(tmp_path / "logs"))
    logging_config = LoggingConfig(
        sinks=[
            LogSinkConfig(type=LogSinkType.FILE),
            LogSinkConfig(type=LogSinkType.NOOP),
        ]
    )

    sink = build_log_sink(logging_config, log_store)

    assert isinstance(sink, CompositeLogSink)
