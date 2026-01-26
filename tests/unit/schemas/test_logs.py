"""Unit tests for log entry schema validation."""

from typing import cast
from uuid import UUID

from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import LogLevel, PhaseName, RunId


def test_log_entry_accepts_nested_json_data() -> None:
    """Ensure log entries accept nested JSON-serializable data."""
    entry = LogEntry(
        timestamp="2026-01-25T12:00:00Z",
        level=LogLevel.INFO,
        event="run_started",
        run_id=cast(RunId, UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")),
        phase=PhaseName.CONTEXT,
        message="Pipeline started",
        data={"stats": {"count": 3, "items": [1, "two", True]}},
    )

    payload = entry.model_dump()
    assert payload["event"] == "run_started"
