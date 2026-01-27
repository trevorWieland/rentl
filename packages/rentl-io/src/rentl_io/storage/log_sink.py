"""Log sink adapter backed by a log store."""

from __future__ import annotations

from collections.abc import Iterable

from rentl_core.ports.orchestrator import LogSinkProtocol
from rentl_core.ports.storage import LogStoreProtocol
from rentl_schemas.logs import LogEntry


class StorageLogSink(LogSinkProtocol):
    """Log sink that persists entries via a LogStoreProtocol."""

    def __init__(self, store: LogStoreProtocol) -> None:
        """Initialize the log sink with a log store."""
        self._store = store

    async def emit_log(self, entry: LogEntry) -> None:
        """Persist a log entry via the backing store."""
        await self._store.append_log(entry)


class CompositeLogSink(LogSinkProtocol):
    """Log sink that forwards entries to multiple sinks."""

    def __init__(self, sinks: Iterable[LogSinkProtocol]) -> None:
        """Initialize the composite log sink."""
        self._sinks = list(sinks)

    async def emit_log(self, entry: LogEntry) -> None:
        """Forward log entries to each sink."""
        for sink in self._sinks:
            await sink.emit_log(entry)
