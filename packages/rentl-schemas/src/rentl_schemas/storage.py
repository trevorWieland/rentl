"""Storage schemas for run state, artifacts, and logs."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.pipeline import RunError, RunMetadata, RunState
from rentl_schemas.primitives import (
    ArtifactId,
    JsonValue,
    LanguageCode,
    PhaseName,
    RunId,
    Timestamp,
)
from rentl_schemas.progress import ProgressSummary

CHECKSUM_PATTERN = r"^[a-f0-9]{64}$"


class StorageBackend(StrEnum):
    """Storage backend identifiers."""

    FILESYSTEM = "filesystem"
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"
    CUSTOM = "custom"


class ArtifactFormat(StrEnum):
    """Artifact serialization formats."""

    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    TXT = "txt"


class ArtifactRole(StrEnum):
    """Artifact role/category for storage indexing."""

    PHASE_OUTPUT = "phase_output"
    LOGS = "logs"
    EXPORT = "export"
    RUN_STATE = "run_state"
    REPORT = "report"
    CUSTOM = "custom"


class StorageReference(BaseSchema):
    """Location reference for stored data."""

    backend: StorageBackend | None = Field(
        None, description="Storage backend identifier"
    )
    path: str | None = Field(
        None, min_length=1, description="Filesystem path if applicable"
    )
    uri: str | None = Field(None, min_length=1, description="Storage URI if applicable")

    @model_validator(mode="after")
    def _validate_location(self) -> StorageReference:
        if self.path is None and self.uri is None:
            raise ValueError("path or uri must be provided")
        return self


class ArtifactMetadata(BaseSchema):
    """Metadata describing a stored artifact."""

    artifact_id: ArtifactId = Field(..., description="Artifact identifier")
    run_id: RunId = Field(..., description="Run identifier")
    role: ArtifactRole = Field(..., description="Artifact role")
    phase: PhaseName | None = Field(None, description="Phase name if applicable")
    target_language: LanguageCode | None = Field(
        None, description="Target language for language-specific artifacts"
    )
    format: ArtifactFormat = Field(..., description="Artifact format")
    created_at: Timestamp = Field(..., description="Artifact creation timestamp")
    location: StorageReference = Field(..., description="Artifact storage location")
    description: str | None = Field(
        None, description="Human-readable artifact description"
    )
    size_bytes: int | None = Field(None, ge=0, description="Artifact size in bytes")
    checksum_sha256: str | None = Field(
        None, pattern=CHECKSUM_PATTERN, description="SHA-256 checksum if available"
    )
    metadata: dict[str, JsonValue] | None = Field(
        None, description="Structured artifact metadata"
    )


class ArtifactManifest(BaseSchema):
    """Manifest describing artifacts for a run."""

    run_id: RunId = Field(..., description="Run identifier")
    generated_at: Timestamp = Field(..., description="Manifest generation timestamp")
    artifacts: list[ArtifactMetadata] = Field(
        ..., description="Artifacts produced by the run"
    )


class LogFileReference(BaseSchema):
    """Reference to a JSONL log file for a run."""

    run_id: RunId = Field(..., description="Run identifier")
    format: ArtifactFormat = Field(ArtifactFormat.JSONL, description="Log file format")
    created_at: Timestamp = Field(..., description="Log file creation timestamp")
    updated_at: Timestamp | None = Field(None, description="Log file update timestamp")
    location: StorageReference = Field(..., description="Log storage location")
    entry_count: int | None = Field(None, ge=0, description="Log entry count if known")


class RunIndexRecord(BaseSchema):
    """Lightweight run record for listing and indexing."""

    metadata: RunMetadata = Field(..., description="Run metadata snapshot")
    project_name: str = Field(..., min_length=1, description="Project name")
    source_language: LanguageCode = Field(..., description="Source language code")
    target_languages: list[LanguageCode] = Field(
        ..., min_length=1, description="Target language codes"
    )
    updated_at: Timestamp = Field(..., description="Last update timestamp")
    progress: ProgressSummary | None = Field(
        None, description="Optional progress summary"
    )
    last_error: RunError | None = Field(
        None, description="Most recent run error if failed"
    )


class RunStateRecord(BaseSchema):
    """Persisted run state snapshot record."""

    run_id: RunId = Field(..., description="Run identifier")
    stored_at: Timestamp = Field(..., description="Snapshot timestamp")
    state: RunState = Field(..., description="Run state snapshot")
    location: StorageReference | None = Field(
        None, description="Storage location for the snapshot"
    )
    checksum_sha256: str | None = Field(
        None, pattern=CHECKSUM_PATTERN, description="SHA-256 checksum if available"
    )
