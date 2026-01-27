"""Event taxonomy and structured payloads for run observability."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    ArtifactId,
    FileFormat,
    LanguageCode,
    PhaseName,
    RunStatus,
)


class RunEvent(StrEnum):
    """Event names for run lifecycle."""

    STARTED = "run_started"
    COMPLETED = "run_completed"
    FAILED = "run_failed"
    CANCELLED = "run_cancelled"


class PhaseEventSuffix(StrEnum):
    """Suffixes for phase lifecycle events."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    INVALIDATED = "invalidated"


class ProgressEvent(StrEnum):
    """Event names for progress updates."""

    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    PHASE_STARTED = "phase_started"
    PHASE_PROGRESS = "phase_progress"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"


class IngestEvent(StrEnum):
    """Event names for ingest operations."""

    STARTED = "ingest_started"
    COMPLETED = "ingest_completed"
    FAILED = "ingest_failed"


class ExportEvent(StrEnum):
    """Event names for export operations."""

    STARTED = "export_started"
    COMPLETED = "export_completed"
    FAILED = "export_failed"


class ArtifactEvent(StrEnum):
    """Event names for artifact persistence."""

    PERSISTED = "artifact_persisted"
    FAILED = "artifact_persist_failed"


class RunStartedData(BaseSchema):
    """Payload for run start events."""

    phases: list[PhaseName] = Field(..., description="Planned phases for the run")


class RunCompletedData(BaseSchema):
    """Payload for run completion events."""

    status: RunStatus = Field(..., description="Final run status")


class RunFailedData(BaseSchema):
    """Payload for run failure events."""

    error_code: str = Field(..., min_length=1, description="Error code")
    why: str = Field(..., min_length=1, description="Reason for failure")
    next_action: str = Field(..., min_length=1, description="Suggested next action")


class PhaseEventData(BaseSchema):
    """Payload for phase lifecycle events."""

    phase: PhaseName = Field(..., description="Phase name")
    revision: int | None = Field(None, ge=1, description="Phase revision number")
    target_language: LanguageCode | None = Field(
        None, description="Target language if applicable"
    )


class IngestStartedData(BaseSchema):
    """Payload for ingest start events."""

    source_path: str = Field(..., min_length=1, description="Input source path")
    format: FileFormat = Field(..., description="Ingest file format")


class IngestCompletedData(IngestStartedData):
    """Payload for ingest completion events."""

    line_count: int = Field(..., ge=0, description="Number of lines ingested")


class IngestFailedData(IngestStartedData):
    """Payload for ingest failure events."""

    error_code: str = Field(..., min_length=1, description="Error code")
    error_message: str = Field(..., min_length=1, description="Error message")
    error_count: int | None = Field(
        None, ge=1, description="Optional total error count"
    )


class ExportStartedData(BaseSchema):
    """Payload for export start events."""

    output_path: str = Field(..., min_length=1, description="Export output path")
    format: FileFormat = Field(..., description="Export file format")


class ExportCompletedData(ExportStartedData):
    """Payload for export completion events."""

    line_count: int = Field(..., ge=0, description="Number of lines exported")
    untranslated_count: int | None = Field(
        None, ge=0, description="Number of untranslated lines detected"
    )
    column_count: int | None = Field(
        None, ge=0, description="Number of CSV columns if applicable"
    )


class ExportFailedData(ExportStartedData):
    """Payload for export failure events."""

    error_code: str = Field(..., min_length=1, description="Error code")
    error_message: str = Field(..., min_length=1, description="Error message")
    error_count: int | None = Field(
        None, ge=1, description="Optional total error count"
    )


class ArtifactPersistedData(BaseSchema):
    """Payload for artifact persisted events."""

    artifact_id: ArtifactId = Field(..., description="Artifact identifier")
    role: str = Field(..., min_length=1, description="Artifact role")
    phase: PhaseName = Field(..., description="Phase that produced the artifact")
    target_language: LanguageCode | None = Field(
        None, description="Target language if applicable"
    )
    format: str = Field(..., min_length=1, description="Artifact format")


class ArtifactPersistFailedData(BaseSchema):
    """Payload for artifact persistence failures."""

    artifact_id: ArtifactId = Field(..., description="Artifact identifier")
    role: str = Field(..., min_length=1, description="Artifact role")
    phase: PhaseName = Field(..., description="Phase that produced the artifact")
    target_language: LanguageCode | None = Field(
        None, description="Target language if applicable"
    )
    format: str = Field(..., min_length=1, description="Artifact format")
    error_message: str = Field(..., min_length=1, description="Error message")
