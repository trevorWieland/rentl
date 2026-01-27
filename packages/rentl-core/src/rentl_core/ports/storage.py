"""Protocol definitions and errors for run persistence and artifact storage."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import ArtifactId, RunId, RunStatus
from rentl_schemas.responses import ErrorDetails, ErrorResponse
from rentl_schemas.storage import (
    ArtifactMetadata,
    LogFileReference,
    RunIndexRecord,
    RunStateRecord,
    StorageBackend,
)

ModelT = TypeVar("ModelT", bound=BaseSchema)


class StorageErrorCode(StrEnum):
    """Categorized error codes for storage operations."""

    NOT_FOUND = "not_found"
    IO_ERROR = "io_error"
    SERIALIZATION_ERROR = "serialization_error"
    VALIDATION_ERROR = "validation_error"
    CONFLICT = "conflict"
    UNSUPPORTED_FORMAT = "unsupported_format"


class StorageErrorDetails(BaseSchema):
    """Detailed storage error context."""

    operation: str | None = Field(None, description="Storage operation name")
    run_id: RunId | None = Field(None, description="Run identifier")
    artifact_id: ArtifactId | None = Field(None, description="Artifact identifier")
    backend: StorageBackend | None = Field(
        None, description="Storage backend identifier"
    )
    path: str | None = Field(None, description="Filesystem path")
    uri: str | None = Field(None, description="Storage URI")
    reason: str | None = Field(None, description="Additional error context")


class StorageErrorInfo(BaseSchema):
    """Structured storage error data."""

    code: StorageErrorCode = Field(..., description="Storage error code")
    message: str = Field(..., min_length=1, description="Error message")
    details: StorageErrorDetails | None = Field(None, description="Error details")

    def to_error_response(self) -> ErrorResponse:
        """Convert storage error info to the standard error response schema.

        Returns:
            ErrorResponse: Standard response error payload.
        """
        details: ErrorDetails | None = None
        if self.details is not None:
            details = ErrorDetails(
                field=self.details.operation,
                provided=self.details.path or self.details.uri,
                valid_options=None,
            )
        return ErrorResponse(
            code=self.code.value, message=self.message, details=details
        )


class StorageError(Exception):
    """Storage error with structured details."""

    def __init__(self, info: StorageErrorInfo) -> None:
        """Initialize the storage error.

        Args:
            info: Structured storage error information.
        """
        super().__init__(info.message)
        self.info = info


class StorageBatchError(Exception):
    """Storage error containing multiple issues."""

    def __init__(self, errors: list[StorageErrorInfo]) -> None:
        """Initialize the batch storage error.

        Args:
            errors: Collected storage errors.
        """
        super().__init__(f"{len(errors)} storage errors")
        self.errors = errors


@runtime_checkable
class RunStateStoreProtocol(Protocol):
    """Protocol for persisting run state and index records."""

    async def save_run_state(self, record: RunStateRecord) -> None:
        """Persist a run state snapshot."""
        raise NotImplementedError

    async def load_run_state(self, run_id: RunId) -> RunStateRecord | None:
        """Load the latest run state snapshot if present."""
        raise NotImplementedError

    async def save_run_index(self, record: RunIndexRecord) -> None:
        """Persist or update a run index record."""
        raise NotImplementedError

    async def list_run_index(
        self,
        status: RunStatus | None = None,
        limit: int | None = None,
    ) -> list[RunIndexRecord]:
        """List run index records for discovery."""
        raise NotImplementedError


@runtime_checkable
class ArtifactStoreProtocol(Protocol):
    """Protocol for persisting and retrieving artifacts."""

    async def write_artifact_json(
        self, metadata: ArtifactMetadata, payload: BaseSchema
    ) -> ArtifactMetadata:
        """Persist a JSON artifact and return enriched metadata."""
        raise NotImplementedError

    async def write_artifact_jsonl(
        self, metadata: ArtifactMetadata, payload: Sequence[BaseSchema]
    ) -> ArtifactMetadata:
        """Persist a JSONL artifact and return enriched metadata."""
        raise NotImplementedError

    async def list_artifacts(self, run_id: RunId) -> list[ArtifactMetadata]:
        """List artifacts for a run."""
        raise NotImplementedError

    async def load_artifact_json(
        self, artifact_id: ArtifactId, model: type[ModelT]
    ) -> ModelT:
        """Load a JSON artifact and parse into the provided model."""
        raise NotImplementedError

    async def load_artifact_jsonl(
        self, artifact_id: ArtifactId, model: type[ModelT]
    ) -> list[ModelT]:
        """Load a JSONL artifact and parse into the provided model."""
        raise NotImplementedError


@runtime_checkable
class LogStoreProtocol(Protocol):
    """Protocol for persisting JSONL log entries."""

    async def append_log(self, entry: LogEntry) -> None:
        """Append a log entry to storage."""
        raise NotImplementedError

    async def append_logs(self, entries: list[LogEntry]) -> None:
        """Append multiple log entries to storage."""
        raise NotImplementedError

    async def get_log_reference(self, run_id: RunId) -> LogFileReference | None:
        """Retrieve the log file reference for a run."""
        raise NotImplementedError
