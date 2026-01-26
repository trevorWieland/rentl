"""Pipeline run state and artifact schemas."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    ArtifactId,
    FileFormat,
    JsonValue,
    PhaseName,
    RunId,
    RunStatus,
    Timestamp,
)
from rentl_schemas.progress import RunProgress
from rentl_schemas.qa import QaSummary
from rentl_schemas.version import VersionInfo


class RunError(BaseSchema):
    """Error details for a failed run or phase."""

    code: str = Field(..., min_length=1, description="Error code")
    message: str = Field(..., min_length=1, description="Error message")
    details: dict[str, JsonValue] | None = Field(
        None, description="Structured error details"
    )


class ArtifactReference(BaseSchema):
    """Reference to an artifact produced by the pipeline."""

    artifact_id: ArtifactId = Field(..., description="Artifact identifier")
    path: str = Field(..., min_length=1, description="Artifact path")
    format: FileFormat = Field(..., description="Artifact format")
    created_at: Timestamp = Field(
        ..., description="ISO-8601 artifact creation timestamp"
    )
    description: str | None = Field(
        None, description="Human-readable artifact description"
    )


class PhaseArtifacts(BaseSchema):
    """Artifacts produced by a specific phase."""

    phase: PhaseName = Field(..., description="Phase name")
    artifacts: list[ArtifactReference] = Field(
        ..., description="Artifacts produced by the phase"
    )


class RunMetadata(BaseSchema):
    """Run identifiers and lifecycle timestamps."""

    run_id: RunId = Field(..., description="Unique run identifier")
    schema_version: VersionInfo = Field(..., description="Schema version for the run")
    status: RunStatus = Field(..., description="Run status")
    current_phase: PhaseName | None = Field(None, description="Current running phase")
    created_at: Timestamp = Field(..., description="Run creation timestamp")
    started_at: Timestamp | None = Field(None, description="Run start timestamp")
    completed_at: Timestamp | None = Field(None, description="Run completion timestamp")


class RunState(BaseSchema):
    """Full pipeline run state snapshot."""

    metadata: RunMetadata = Field(..., description="Run metadata")
    progress: RunProgress = Field(..., description="Run progress")
    artifacts: list[PhaseArtifacts] = Field(..., description="Phase artifacts")
    last_error: RunError | None = Field(None, description="Most recent error if failed")
    qa_summary: QaSummary | None = Field(
        None, description="Aggregate QA summary for the run"
    )
