"""Protocol definitions and helpers for pipeline orchestration."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.events import (
    ArtifactEvent,
    ArtifactPersistedData,
    ArtifactPersistFailedData,
    PhaseEventData,
    PhaseEventSuffix,
    RunCompletedData,
    RunEvent,
    RunFailedData,
    RunStartedData,
)
from rentl_schemas.logs import LogEntry
from rentl_schemas.phases import (
    ContextPhaseInput,
    ContextPhaseOutput,
    EditPhaseInput,
    EditPhaseOutput,
    PretranslationPhaseInput,
    PretranslationPhaseOutput,
    QaPhaseInput,
    QaPhaseOutput,
    TranslatePhaseInput,
    TranslatePhaseOutput,
)
from rentl_schemas.primitives import (
    JsonValue,
    LanguageCode,
    LogLevel,
    PhaseName,
    RunId,
    RunStatus,
    Timestamp,
)
from rentl_schemas.progress import ProgressUpdate
from rentl_schemas.responses import ErrorDetails, ErrorResponse
from rentl_schemas.storage import ArtifactMetadata

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT_co = TypeVar("OutputT_co", bound=BaseSchema, covariant=True)


@runtime_checkable
class PhaseAgentProtocol(Protocol[InputT, OutputT_co]):
    """Protocol for a single phase agent."""

    async def run(self, payload: InputT) -> OutputT_co:
        """Execute the phase logic for a single payload."""
        raise NotImplementedError


@runtime_checkable
class PhaseAgentPoolProtocol(Protocol[InputT, OutputT_co]):
    """Protocol for a pool of phase agents executing in batch.

    Implementations must preserve output ordering aligned with the input payloads.
    """

    async def run_batch(self, payloads: list[InputT]) -> list[OutputT_co]:
        """Execute the phase logic for a batch of payloads."""
        raise NotImplementedError


type ContextAgentProtocol = PhaseAgentProtocol[ContextPhaseInput, ContextPhaseOutput]
type ContextAgentPoolProtocol = PhaseAgentPoolProtocol[
    ContextPhaseInput, ContextPhaseOutput
]
type PretranslationAgentProtocol = PhaseAgentProtocol[
    PretranslationPhaseInput, PretranslationPhaseOutput
]
type PretranslationAgentPoolProtocol = PhaseAgentPoolProtocol[
    PretranslationPhaseInput, PretranslationPhaseOutput
]
type TranslateAgentProtocol = PhaseAgentProtocol[
    TranslatePhaseInput, TranslatePhaseOutput
]
type TranslateAgentPoolProtocol = PhaseAgentPoolProtocol[
    TranslatePhaseInput, TranslatePhaseOutput
]
type QaAgentProtocol = PhaseAgentProtocol[QaPhaseInput, QaPhaseOutput]
type QaAgentPoolProtocol = PhaseAgentPoolProtocol[QaPhaseInput, QaPhaseOutput]
type EditAgentProtocol = PhaseAgentProtocol[EditPhaseInput, EditPhaseOutput]
type EditAgentPoolProtocol = PhaseAgentPoolProtocol[EditPhaseInput, EditPhaseOutput]


@runtime_checkable
class LogSinkProtocol(Protocol):
    """Protocol for emitting JSONL log entries."""

    async def emit_log(self, entry: LogEntry) -> None:
        """Emit a log entry."""
        raise NotImplementedError


@runtime_checkable
class ProgressSinkProtocol(Protocol):
    """Protocol for emitting progress updates."""

    async def emit_progress(self, update: ProgressUpdate) -> None:
        """Emit a progress update."""
        raise NotImplementedError


class OrchestrationErrorCode(StrEnum):
    """Categorized error codes for orchestration failures."""

    MISSING_DEPENDENCY = "missing_dependency"
    PHASE_NOT_CONFIGURED = "phase_not_configured"
    PHASE_DISABLED = "phase_disabled"
    INVALID_STATE = "invalid_state"
    PHASE_EXECUTION_FAILED = "phase_execution_failed"


class OrchestrationErrorDetails(BaseSchema):
    """Detailed orchestration error context."""

    phase: PhaseName | None = Field(None, description="Phase associated with error")
    target_language: LanguageCode | None = Field(
        None, description="Target language if applicable"
    )
    missing_phases: list[PhaseName] | None = Field(
        None, description="Missing prerequisite phases"
    )
    reason: str | None = Field(None, description="Additional error context")


class OrchestrationErrorInfo(BaseSchema):
    """Structured orchestration error data."""

    code: OrchestrationErrorCode = Field(..., description="Error code")
    message: str = Field(..., min_length=1, description="Error message")
    details: OrchestrationErrorDetails | None = Field(None, description="Error details")

    def to_error_response(self) -> ErrorResponse:
        """Convert orchestration error info to standard error response.

        Returns:
            ErrorResponse: Standard response error payload.
        """
        details: ErrorDetails | None = None
        if self.details is not None and self.details.phase is not None:
            phase_value = self.details.phase
            if isinstance(phase_value, PhaseName):
                provided = phase_value.value
            else:
                provided = str(phase_value)
            details = ErrorDetails(
                field="phase",
                provided=provided,
                valid_options=None,
            )
        code_value = getattr(self.code, "value", self.code)
        return ErrorResponse(
            code=str(code_value), message=self.message, details=details
        )


class OrchestrationError(Exception):
    """Orchestration error with structured details."""

    def __init__(self, info: OrchestrationErrorInfo) -> None:
        """Initialize the orchestration error.

        Args:
            info: Structured orchestration error information.
        """
        super().__init__(info.message)
        self.info = info


def build_run_started_log(
    timestamp: Timestamp, run_id: RunId, phases: list[PhaseName]
) -> LogEntry:
    """Build a log entry for run start.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        phases: Planned phases for the run.

    Returns:
        LogEntry: Structured run start log entry.
    """
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=RunEvent.STARTED,
        run_id=run_id,
        phase=None,
        message="Run started",
        data=RunStartedData(phases=phases).model_dump(exclude_none=True),
    )


def build_run_completed_log(
    timestamp: Timestamp, run_id: RunId, status: RunStatus
) -> LogEntry:
    """Build a log entry for run completion.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        status: Final run status.

    Returns:
        LogEntry: Structured run completion log entry.
    """
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=RunEvent.COMPLETED,
        run_id=run_id,
        phase=None,
        message="Run completed",
        data=RunCompletedData(status=status).model_dump(exclude_none=True),
    )


def build_run_failed_log(
    timestamp: Timestamp,
    run_id: RunId,
    message: str,
    error_code: str,
    why: str,
    next_action: str,
) -> LogEntry:
    """Build a log entry for run failure.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        message: Failure message.
        error_code: Error code describing the failure.
        why: Reason for the failure.
        next_action: Suggested next action.

    Returns:
        LogEntry: Structured run failure log entry.
    """
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.ERROR,
        event=RunEvent.FAILED,
        run_id=run_id,
        phase=None,
        message=message,
        data=RunFailedData(
            error_code=error_code, why=why, next_action=next_action
        ).model_dump(exclude_none=True),
    )


def build_phase_event_name(phase: PhaseName, suffix: PhaseEventSuffix) -> str:
    """Build a phase-specific event name.

    Args:
        phase: Phase name.
        suffix: Event suffix (e.g., started, completed).

    Returns:
        str: Event name in snake_case.
    """
    return f"{phase.value}_{suffix.value}"


def build_phase_log(
    timestamp: Timestamp,
    run_id: RunId,
    phase: PhaseName,
    event_suffix: PhaseEventSuffix,
    message: str,
    data: dict[str, JsonValue] | None = None,
    level: LogLevel = LogLevel.INFO,
) -> LogEntry:
    """Build a log entry for a phase lifecycle event.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        phase: Phase name.
        event_suffix: Event suffix (started/completed/failed/blocked/invalidated).
        message: Log message.
        data: Structured event data.
        level: Log level.

    Returns:
        LogEntry: Structured phase log entry.
    """
    revision_value: int | None = None
    target_language_value: LanguageCode | None = None
    if data is not None:
        revision = data.get("revision")
        if isinstance(revision, int):
            revision_value = revision
        target_language = data.get("target_language")
        if isinstance(target_language, str):
            target_language_value = target_language
    payload = PhaseEventData(
        phase=phase,
        revision=revision_value,
        target_language=target_language_value,
    )
    extra: dict[str, JsonValue] = {}
    if data is not None:
        extra = {
            key: value
            for key, value in data.items()
            if key not in {"phase", "revision", "target_language"}
        }
    return LogEntry(
        timestamp=timestamp,
        level=level,
        event=build_phase_event_name(phase, event_suffix),
        run_id=run_id,
        phase=phase,
        message=message,
        data={**payload.model_dump(exclude_none=True), **extra},
    )


def build_artifact_persisted_log(
    timestamp: Timestamp, run_id: RunId, metadata: ArtifactMetadata
) -> LogEntry:
    """Build a log entry for artifact persistence.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        metadata: Stored artifact metadata.

    Returns:
        LogEntry: Structured artifact persisted log entry.

    Raises:
        ValueError: If artifact metadata is missing the phase.
    """
    if metadata.phase is None:
        raise ValueError("artifact metadata must include phase")
    phase = metadata.phase
    phase_value = PhaseName(phase)
    role_value = getattr(metadata.role, "value", metadata.role)
    format_value = getattr(metadata.format, "value", metadata.format)
    data = ArtifactPersistedData(
        artifact_id=metadata.artifact_id,
        role=str(role_value),
        phase=phase_value,
        target_language=metadata.target_language,
        format=str(format_value),
    ).model_dump(exclude_none=True)
    if "artifact_id" in data:
        data["artifact_id"] = str(data["artifact_id"])
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=ArtifactEvent.PERSISTED,
        run_id=run_id,
        phase=phase_value,
        message="Artifact persisted",
        data=data,
    )


def build_artifact_persist_failed_log(
    timestamp: Timestamp,
    run_id: RunId,
    metadata: ArtifactMetadata,
    error_message: str,
) -> LogEntry:
    """Build a log entry for artifact persistence failure.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        metadata: Artifact metadata attempted.
        error_message: Failure message.

    Returns:
        LogEntry: Structured artifact failure log entry.

    Raises:
        ValueError: If artifact metadata is missing the phase.
    """
    if metadata.phase is None:
        raise ValueError("artifact metadata must include phase")
    phase = metadata.phase
    phase_value = PhaseName(phase)
    role_value = getattr(metadata.role, "value", metadata.role)
    format_value = getattr(metadata.format, "value", metadata.format)
    data = ArtifactPersistFailedData(
        artifact_id=metadata.artifact_id,
        role=str(role_value),
        phase=phase_value,
        target_language=metadata.target_language,
        format=str(format_value),
        error_message=error_message,
    ).model_dump(exclude_none=True)
    if "artifact_id" in data:
        data["artifact_id"] = str(data["artifact_id"])
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.ERROR,
        event=ArtifactEvent.FAILED,
        run_id=run_id,
        phase=phase_value,
        message="Artifact persistence failed",
        data=data,
    )
