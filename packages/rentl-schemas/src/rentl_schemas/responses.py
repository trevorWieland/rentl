"""API response envelope schemas for CLI output."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.pipeline import PhaseRunRecord, RunState
from rentl_schemas.primitives import (
    PhaseName,
    RequestId,
    RunId,
    RunStatus,
    Timestamp,
)
from rentl_schemas.progress import (
    AgentTelemetry,
    AgentTelemetrySummary,
    ProgressSummary,
    RunProgress,
)
from rentl_schemas.storage import LogFileReference, StorageReference


class MetaInfo(BaseSchema):
    """Metadata for API responses."""

    timestamp: Timestamp = Field(..., description="ISO-8601 response timestamp")
    request_id: RequestId | None = Field(
        None, description="Optional request identifier"
    )


class ErrorDetails(BaseSchema):
    """Detailed error context for responses."""

    field: str | None = Field(None, description="Field name if applicable")
    provided: str | None = Field(None, description="Provided value")
    valid_options: list[str] | None = Field(
        None, description="Valid options if applicable"
    )


class ErrorResponse(BaseSchema):
    """Error information in response."""

    code: str = Field(..., min_length=1, description="Error code")
    message: str = Field(..., min_length=1, description="Error message")
    details: ErrorDetails | None = Field(None, description="Optional error details")


class ApiResponse[ResponseData](BaseSchema):
    """Generic API response envelope."""

    data: ResponseData | None = Field(
        None, description="Success payload, null on error"
    )
    error: ErrorResponse | None = Field(
        None, description="Error information, null on success"
    )
    meta: MetaInfo = Field(..., description="Response metadata")


class RunExecutionResult(BaseSchema):
    """Result payload for CLI run commands."""

    run_id: RunId = Field(..., description="Run identifier")
    status: RunStatus = Field(..., description="Run status")
    progress: ProgressSummary | None = Field(None, description="Run progress summary")
    run_state: RunState | None = Field(None, description="Latest run state snapshot")
    log_file: LogFileReference | None = Field(None, description="Log file reference")
    progress_file: StorageReference | None = Field(
        None, description="Progress stream file reference"
    )
    phase_record: PhaseRunRecord | None = Field(
        None, description="Phase run record when running a single phase"
    )


class RunStatusResult(BaseSchema):
    """Result payload for CLI status command."""

    run_id: RunId = Field(..., description="Run identifier")
    status: RunStatus = Field(..., description="Run status")
    current_phase: PhaseName | None = Field(None, description="Current phase")
    updated_at: Timestamp = Field(..., description="Status snapshot timestamp")
    progress: RunProgress | None = Field(
        None, description="Latest run progress snapshot"
    )
    run_state: RunState | None = Field(None, description="Latest run state snapshot")
    agent_summary: AgentTelemetrySummary | None = Field(
        None, description="Agent telemetry summary"
    )
    agents: list[AgentTelemetry] | None = Field(
        None, description="Latest agent telemetry snapshots"
    )
    log_file: LogFileReference | None = Field(None, description="Log file reference")
    progress_file: StorageReference | None = Field(
        None, description="Progress stream file reference"
    )
