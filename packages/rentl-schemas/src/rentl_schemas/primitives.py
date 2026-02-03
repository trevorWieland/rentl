"""Primitive types and enums shared across rentl schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, Field

HUMAN_ID_PATTERN = r"^[a-z]+_[0-9]+$"
ISO_8601_PATTERN = (
    r"^\d{4}-\d{2}-\d{2}T"
    r"\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)
LANGUAGE_CODE_PATTERN = r"^[a-z]{2}(?:-[A-Z]{2})?$"
EVENT_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"


def _validate_uuid7(value: UUID) -> UUID:
    """Ensure UUID values are version 7.

    Args:
        value: Parsed UUID value.

    Returns:
        UUID: The validated UUIDv7 value.

    Raises:
        ValueError: If the UUID is not version 7.
    """
    if value.version != 7:
        raise ValueError("UUID must be version 7")
    return value


type Uuid7 = Annotated[UUID, AfterValidator(_validate_uuid7)]
type HumanReadableId = Annotated[str, Field(pattern=HUMAN_ID_PATTERN)]

type RunId = Uuid7
type PhaseRunId = Uuid7
type IssueId = Uuid7
type ArtifactId = Uuid7
type NoteId = Uuid7
type RequestId = Uuid7
type AnnotationId = Uuid7
type LineId = HumanReadableId
type SceneId = HumanReadableId
type RouteId = HumanReadableId
type Timestamp = Annotated[str, Field(pattern=ISO_8601_PATTERN)]
type LanguageCode = Annotated[str, Field(pattern=LANGUAGE_CODE_PATTERN)]
type EventName = Annotated[str, Field(pattern=EVENT_NAME_PATTERN)]
type AnnotationType = Annotated[str, Field(pattern=EVENT_NAME_PATTERN)]

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class PhaseName(StrEnum):
    """Pipeline phase names."""

    INGEST = "ingest"
    CONTEXT = "context"
    PRETRANSLATION = "pretranslation"
    TRANSLATE = "translate"
    QA = "qa"
    EDIT = "edit"
    EXPORT = "export"


PIPELINE_PHASE_ORDER = [
    PhaseName.INGEST,
    PhaseName.CONTEXT,
    PhaseName.PRETRANSLATION,
    PhaseName.TRANSLATE,
    PhaseName.QA,
    PhaseName.EDIT,
    PhaseName.EXPORT,
]


class FileFormat(StrEnum):
    """Supported file formats for ingest and export."""

    CSV = "csv"
    JSONL = "jsonl"
    TXT = "txt"


class UntranslatedPolicy(StrEnum):
    """Policy for handling untranslated lines during export."""

    ERROR = "error"
    WARN = "warn"
    ALLOW = "allow"


class RunStatus(StrEnum):
    """Overall run status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseStatus(StrEnum):
    """Phase execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PhaseWorkStrategy(StrEnum):
    """Work splitting strategy for multi-agent phase execution."""

    FULL = "full"
    SCENE = "scene"
    CHUNK = "chunk"
    ROUTE = "route"


class LogLevel(StrEnum):
    """Log level values for JSONL logs."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class LogSinkType(StrEnum):
    """Supported log sink types."""

    CONSOLE = "console"
    FILE = "file"
    NOOP = "noop"


class QaSeverity(StrEnum):
    """QA issue severity levels."""

    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class QaCategory(StrEnum):
    """QA issue categories for v0.1 and v0.2 readiness."""

    GRAMMAR = "grammar"
    TERMINOLOGY = "terminology"
    STYLE = "style"
    CONSISTENCY = "consistency"
    FORMATTING = "formatting"
    CONTEXT = "context"
    CULTURAL = "cultural"
    OTHER = "other"


class ReasoningEffort(StrEnum):
    """Reasoning effort levels for LLM requests."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
