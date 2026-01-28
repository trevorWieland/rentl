"""Pipeline run state and artifact schemas."""

from __future__ import annotations

from pydantic import Field, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    ArtifactId,
    FileFormat,
    JsonValue,
    LanguageCode,
    PhaseName,
    PhaseRunId,
    PhaseStatus,
    RunId,
    RunStatus,
    Timestamp,
)
from rentl_schemas.progress import RunProgress
from rentl_schemas.qa import QaSummary
from rentl_schemas.results import PhaseResultSummary
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
    uri: str | None = Field(
        None, min_length=1, description="Artifact storage URI if applicable"
    )
    format: FileFormat = Field(..., description="Artifact format")
    created_at: Timestamp = Field(
        ..., description="ISO-8601 artifact creation timestamp"
    )
    description: str | None = Field(
        None, description="Human-readable artifact description"
    )


class PhaseDependency(BaseSchema):
    """Dependency reference for a phase output."""

    phase: PhaseName = Field(..., description="Dependent phase name")
    revision: int = Field(..., ge=1, description="Dependent phase revision")
    target_language: LanguageCode | None = Field(
        None, description="Target language for the dependency if applicable"
    )


class PhaseRevision(BaseSchema):
    """Latest revision marker for a phase output."""

    phase: PhaseName = Field(..., description="Phase name")
    revision: int = Field(..., ge=1, description="Latest revision number")
    target_language: LanguageCode | None = Field(
        None, description="Target language for the revision if applicable"
    )


class PhaseRunRecord(BaseSchema):
    """History record for a single phase execution."""

    phase_run_id: PhaseRunId = Field(..., description="Unique phase run identifier")
    phase: PhaseName = Field(..., description="Phase name")
    revision: int = Field(..., ge=1, description="Phase revision number")
    status: PhaseStatus = Field(..., description="Phase execution status")
    target_language: LanguageCode | None = Field(
        None, description="Target language for language-specific phases"
    )
    dependencies: list[PhaseDependency] | None = Field(
        None, description="Dependencies used to produce this output"
    )
    artifact_ids: list[ArtifactId] | None = Field(
        None, description="Artifacts produced by this phase run"
    )
    started_at: Timestamp | None = Field(None, description="Phase start timestamp")
    completed_at: Timestamp | None = Field(
        None, description="Phase completion timestamp"
    )
    stale: bool = Field(False, description="Whether the output is stale")
    error: RunError | None = Field(None, description="Error details if failed")
    summary: PhaseResultSummary | None = Field(
        None, description="Phase result summary metrics"
    )
    message: str | None = Field(
        None, description="Optional message about the phase run"
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
    phase_history: list[PhaseRunRecord] | None = Field(
        None, description="Phase run history"
    )
    phase_revisions: list[PhaseRevision] | None = Field(
        None, description="Latest phase revisions by phase and target language"
    )
    last_error: RunError | None = Field(None, description="Most recent error if failed")
    qa_summary: QaSummary | None = Field(
        None, description="Aggregate QA summary for the run"
    )

    @model_validator(mode="after")
    def _validate_phase_revisions(self) -> RunState:
        if self.phase_revisions is None:
            return self
        seen: set[tuple[PhaseName, LanguageCode | None]] = set()
        for entry in self.phase_revisions:
            key = (entry.phase, entry.target_language)
            if key in seen:
                raise ValueError(
                    "phase_revisions must be unique by phase and target_language"
                )
            seen.add(key)
        return self
