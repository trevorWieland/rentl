"""Log sink adapters for pipeline events."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TextIO

from rentl_core.ports.orchestrator import LogSinkProtocol
from rentl_core.ports.storage import LogStoreProtocol
from rentl_schemas.config import LoggingConfig
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import LogLevel, LogSinkType

if TYPE_CHECKING:
    from rentl_schemas.redaction import Redactor


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


class ConsoleLogSink(LogSinkProtocol):
    """Log sink that writes JSONL entries to stdout."""

    def __init__(self, stream: TextIO | None = None) -> None:
        """Initialize the console log sink.

        Args:
            stream: Output stream to write JSONL log entries.
        """
        self._stream = stream or sys.stderr

    async def emit_log(self, entry: LogEntry) -> None:
        """Write log entry JSONL to the output stream."""
        payload = entry.model_dump_json(exclude_none=False)
        self._stream.write(payload + "\n")
        self._stream.flush()


class NoopLogSink(LogSinkProtocol):
    """Log sink that drops all log entries."""

    async def emit_log(self, entry: LogEntry) -> None:
        """Ignore log entries."""
        return None


class RedactingLogSink(LogSinkProtocol):
    """Log sink wrapper that redacts secrets before forwarding to a delegate sink."""

    def __init__(self, delegate: LogSinkProtocol, redactor: Redactor) -> None:
        """Initialize the redacting log sink.

        Args:
            delegate: Underlying sink to forward redacted entries to
            redactor: Redactor instance to apply before writing
        """
        self._delegate = delegate
        self._redactor = redactor

    async def emit_log(self, entry: LogEntry) -> None:
        """Redact secrets from entry before forwarding to delegate sink."""
        # Redact the message field
        redacted_message = self._redactor.redact(entry.message)

        # Redact the data field if present
        redacted_data = None
        if entry.data is not None:
            redacted_data = self._redactor.redact_dict(entry.data)

        # Detect if redaction occurred
        message_changed = redacted_message != entry.message
        data_changed = entry.data is not None and redacted_data != entry.data

        # Create a new entry with redacted values
        redacted_entry = entry.model_copy(
            update={"message": redacted_message, "data": redacted_data}
        )

        # Forward to delegate
        await self._delegate.emit_log(redacted_entry)

        # Emit a debug log if redaction occurred
        if message_changed or data_changed:
            debug_entry = LogEntry(
                timestamp=datetime.now(UTC).isoformat(),
                level=LogLevel.DEBUG,
                event="redaction_applied",
                run_id=entry.run_id,
                phase=entry.phase,
                message="Secret redaction applied to log entry",
                data={
                    "original_event": entry.event,
                    "message_redacted": message_changed,
                    "data_redacted": data_changed,
                },
            )
            await self._delegate.emit_log(debug_entry)


def build_log_sink(
    logging_config: LoggingConfig,
    log_store: LogStoreProtocol,
    *,
    stream: TextIO | None = None,
    redactor: Redactor | None = None,
) -> LogSinkProtocol:
    """Build a log sink from configuration.

    Args:
        logging_config: Logging configuration for the run.
        log_store: Log store for file-backed logging.
        stream: Optional stream for console logging.
        redactor: Optional redactor to apply before writing logs.

    Returns:
        LogSinkProtocol: Configured log sink.

    Raises:
        ValueError: If an unsupported log sink type is configured.
    """
    sinks: list[LogSinkProtocol] = []
    for sink_config in logging_config.sinks:
        if sink_config.type == LogSinkType.FILE:
            sinks.append(StorageLogSink(log_store))
        elif sink_config.type == LogSinkType.CONSOLE:
            sinks.append(ConsoleLogSink(stream=stream))
        elif sink_config.type == LogSinkType.NOOP:
            sinks.append(NoopLogSink())
        else:
            raise ValueError(f"Unsupported log sink type: {sink_config.type}")

    # Wrap each sink with redaction if a redactor is provided
    if redactor is not None:
        sinks = [RedactingLogSink(sink, redactor) for sink in sinks]

    if len(sinks) == 1:
        return sinks[0]
    return CompositeLogSink(sinks)
