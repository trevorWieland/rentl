"""Progress sink adapters for streaming updates."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from pathlib import Path

from rentl_core.ports.orchestrator import ProgressSinkProtocol
from rentl_schemas.base import BaseSchema
from rentl_schemas.progress import ProgressUpdate


class FileSystemProgressSink(ProgressSinkProtocol):
    """Progress sink that appends JSONL updates to a file."""

    def __init__(self, path: str) -> None:
        """Initialize the progress sink with a file path."""
        self._path = Path(path)

    async def emit_progress(self, update: ProgressUpdate) -> None:
        """Append a progress update to the JSONL file."""
        await asyncio.to_thread(_append_jsonl, self._path, update)


class InMemoryProgressSink(ProgressSinkProtocol):
    """Progress sink that stores updates in memory."""

    def __init__(self) -> None:
        """Initialize the in-memory progress sink."""
        self._updates: list[ProgressUpdate] = []

    @property
    def updates(self) -> list[ProgressUpdate]:
        """Return a copy of stored progress updates."""
        return list(self._updates)

    async def emit_progress(self, update: ProgressUpdate) -> None:
        """Store a progress update in memory."""
        self._updates.append(update)


class CompositeProgressSink(ProgressSinkProtocol):
    """Progress sink that forwards updates to multiple sinks."""

    def __init__(self, sinks: Iterable[ProgressSinkProtocol]) -> None:
        """Initialize the composite progress sink."""
        self._sinks = list(sinks)

    async def emit_progress(self, update: ProgressUpdate) -> None:
        """Forward progress updates to each sink."""
        for sink in self._sinks:
            await sink.emit_progress(update)


def _append_jsonl(path: Path, payload: BaseSchema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_json = payload.model_dump_json(exclude_none=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(payload_json + "\n")
