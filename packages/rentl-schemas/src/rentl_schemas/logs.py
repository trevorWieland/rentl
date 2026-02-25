"""JSONL log entry schema for pipeline events."""

from __future__ import annotations

from pydantic import Field, field_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    EventName,
    JsonValue,
    LogLevel,
    PhaseName,
    RunId,
    Timestamp,
)


class LogEntry(BaseSchema):
    """Single log line in JSONL format."""

    timestamp: Timestamp = Field(
        ..., description="ISO-8601 timestamp for the log entry"
    )
    level: LogLevel = Field(..., description="Log level")
    event: EventName = Field(..., description="Event name")
    run_id: RunId = Field(..., description="Pipeline run identifier")
    phase: PhaseName | None = Field(None, description="Pipeline phase if applicable")

    @field_validator("phase", mode="before")
    @classmethod
    def _coerce_phase(cls, value: str | PhaseName | None) -> PhaseName | None:
        if value is None:
            return None
        if isinstance(value, PhaseName):
            return value
        return PhaseName(value)

    message: str = Field(..., min_length=1, description="Log message")
    data: dict[str, JsonValue] | None = Field(None, description="Structured event data")
