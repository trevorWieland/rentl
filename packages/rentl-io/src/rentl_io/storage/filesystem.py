"""Filesystem-backed storage adapters."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Protocol, TypeVar, cast

from pydantic import ValidationError

from rentl_core.ports.storage import (
    ArtifactStoreProtocol,
    LogStoreProtocol,
    RunStateStoreProtocol,
    StorageError,
    StorageErrorCode,
    StorageErrorDetails,
    StorageErrorInfo,
)
from rentl_schemas.base import BaseSchema
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import ArtifactId, RunId, RunStatus, Timestamp
from rentl_schemas.storage import (
    ArtifactFormat,
    ArtifactMetadata,
    LogFileReference,
    RunIndexRecord,
    RunStateRecord,
    StorageBackend,
    StorageReference,
)

ModelT = TypeVar("ModelT", bound=BaseSchema)


class _SchemaModel(Protocol):
    @classmethod
    def model_validate_json(cls, json_data: str) -> BaseSchema: ...


class FileSystemRunStateStore(RunStateStoreProtocol):
    """Filesystem-backed run state store."""

    def __init__(
        self,
        base_dir: str,
        backend: StorageBackend = StorageBackend.FILESYSTEM,
    ) -> None:
        """Initialize the run state store."""
        self._base_dir = Path(base_dir)
        self._state_dir = self._base_dir / "runs"
        self._index_dir = self._base_dir / "index"
        self._backend = backend

    async def save_run_state(self, record: RunStateRecord) -> None:
        """Persist a run state snapshot to disk.

        Raises:
            StorageError: If the snapshot cannot be written.
        """
        path = self._state_dir / f"{record.run_id}.json"
        try:
            await asyncio.to_thread(_write_json_file, path, record)
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="save_run_state",
                        run_id=record.run_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    async def load_run_state(self, run_id: RunId) -> RunStateRecord | None:
        """Load a run state snapshot if present.

        Returns:
            RunStateRecord | None: Stored run state if available.

        Raises:
            StorageError: If the snapshot cannot be read.
        """
        path = self._state_dir / f"{run_id}.json"
        if not await asyncio.to_thread(path.exists):
            return None
        try:
            return await asyncio.to_thread(_read_run_state_record, path)
        except (ValidationError, JSONDecodeError, ValueError) as exc:
            error_info = _build_record_parse_error_info(
                entity="Run state snapshot",
                operation="load_run_state",
                run_id=run_id,
                path=path,
                backend=self._backend,
                exc=exc,
            )
            raise StorageError(error_info) from exc
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="load_run_state",
                        run_id=run_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    async def save_run_index(self, record: RunIndexRecord) -> None:
        """Persist a run index record to disk.

        Raises:
            StorageError: If the index record cannot be written.
        """
        path = self._index_dir / f"{record.metadata.run_id}.json"
        try:
            await asyncio.to_thread(_write_json_file, path, record)
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="save_run_index",
                        run_id=record.metadata.run_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    async def list_run_index(
        self,
        status: RunStatus | None = None,
        limit: int | None = None,
    ) -> list[RunIndexRecord]:
        """List run index records from disk.

        Returns:
            list[RunIndexRecord]: Run index records ordered by update time.

        Raises:
            StorageError: If index records cannot be read.
        """
        if not await asyncio.to_thread(self._index_dir.exists):
            return []
        try:
            records = await asyncio.to_thread(_read_run_index_records, self._index_dir)
        except (ValidationError, JSONDecodeError, ValueError) as exc:
            error_info = _build_record_parse_error_info(
                entity="Run index record",
                operation="list_run_index",
                path=self._index_dir,
                backend=self._backend,
                exc=exc,
            )
            raise StorageError(error_info) from exc
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="list_run_index",
                        backend=self._backend,
                        path=str(self._index_dir),
                    ),
                )
            ) from exc
        if status is not None:
            records = [record for record in records if record.metadata.status == status]
        records.sort(key=lambda record: record.updated_at, reverse=True)
        if limit is not None:
            return records[:limit]
        return records


class FileSystemArtifactStore(ArtifactStoreProtocol):
    """Filesystem-backed artifact store."""

    def __init__(
        self,
        base_dir: str,
        backend: StorageBackend = StorageBackend.FILESYSTEM,
    ) -> None:
        """Initialize the artifact store."""
        self._base_dir = Path(base_dir)
        self._index_path = self._base_dir / "index.jsonl"
        self._backend = backend

    async def write_artifact_json(
        self, metadata: ArtifactMetadata, payload: BaseSchema
    ) -> ArtifactMetadata:
        """Write a JSON artifact and return stored metadata.

        Returns:
            ArtifactMetadata: Stored metadata with location populated.

        Raises:
            StorageError: If the artifact cannot be written.
        """
        if metadata.format != ArtifactFormat.JSON:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.UNSUPPORTED_FORMAT,
                    message="Artifact format must be json",
                    details=StorageErrorDetails(
                        operation="write_artifact_json",
                        run_id=metadata.run_id,
                        artifact_id=metadata.artifact_id,
                        backend=self._backend,
                    ),
                )
            )
        path = self._artifact_path(
            metadata.run_id, metadata.artifact_id, metadata.format
        )
        stored = self._with_location(metadata, path)
        try:
            await asyncio.to_thread(_write_json_file, path, payload)
            await asyncio.to_thread(_append_jsonl, self._index_path, stored)
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="write_artifact_json",
                        run_id=metadata.run_id,
                        artifact_id=metadata.artifact_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc
        return stored

    async def write_artifact_jsonl(
        self, metadata: ArtifactMetadata, payload: Sequence[BaseSchema]
    ) -> ArtifactMetadata:
        """Write a JSONL artifact and return stored metadata.

        Returns:
            ArtifactMetadata: Stored metadata with location populated.

        Raises:
            StorageError: If the artifact cannot be written.
        """
        if metadata.format != ArtifactFormat.JSONL:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.UNSUPPORTED_FORMAT,
                    message="Artifact format must be jsonl",
                    details=StorageErrorDetails(
                        operation="write_artifact_jsonl",
                        run_id=metadata.run_id,
                        artifact_id=metadata.artifact_id,
                        backend=self._backend,
                    ),
                )
            )
        path = self._artifact_path(
            metadata.run_id, metadata.artifact_id, metadata.format
        )
        stored = self._with_location(metadata, path)
        try:
            await asyncio.to_thread(_write_jsonl_file, path, payload)
            await asyncio.to_thread(_append_jsonl, self._index_path, stored)
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="write_artifact_jsonl",
                        run_id=metadata.run_id,
                        artifact_id=metadata.artifact_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc
        return stored

    async def list_artifacts(self, run_id: RunId) -> list[ArtifactMetadata]:
        """List stored artifacts for a run.

        Returns:
            list[ArtifactMetadata]: Stored artifacts for the run.

        Raises:
            StorageError: If artifacts cannot be read.
        """
        if not await asyncio.to_thread(self._index_path.exists):
            return []
        try:
            return await asyncio.to_thread(
                _read_artifacts_for_run, self._index_path, run_id
            )
        except (ValidationError, JSONDecodeError, ValueError) as exc:
            error_info = _build_record_parse_error_info(
                entity="Artifact index entry",
                operation="list_artifacts",
                run_id=run_id,
                path=self._index_path,
                backend=self._backend,
                exc=exc,
            )
            raise StorageError(error_info) from exc
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="list_artifacts",
                        run_id=run_id,
                        backend=self._backend,
                        path=str(self._index_path),
                    ),
                )
            ) from exc

    async def load_artifact_json(
        self, artifact_id: ArtifactId, model: type[ModelT]
    ) -> ModelT:
        """Load a JSON artifact and parse it into the provided model.

        Returns:
            ModelT: Parsed artifact payload.

        Raises:
            StorageError: If the artifact is missing or unreadable.
        """
        try:
            metadata = await asyncio.to_thread(
                _find_artifact_metadata, self._index_path, artifact_id
            )
        except (ValidationError, JSONDecodeError, ValueError) as exc:
            error_info = _build_record_parse_error_info(
                entity="Artifact index entry",
                operation="load_artifact_json",
                artifact_id=artifact_id,
                path=self._index_path,
                backend=self._backend,
                exc=exc,
            )
            raise StorageError(error_info) from exc
        if metadata is None:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.NOT_FOUND,
                    message="Artifact not found",
                    details=StorageErrorDetails(
                        operation="load_artifact_json",
                        artifact_id=artifact_id,
                        backend=self._backend,
                    ),
                )
            )
        if metadata.format != ArtifactFormat.JSON:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.UNSUPPORTED_FORMAT,
                    message="Artifact is not JSON",
                    details=StorageErrorDetails(
                        operation="load_artifact_json",
                        artifact_id=artifact_id,
                        backend=self._backend,
                    ),
                )
            )
        path = _location_path(metadata)
        try:
            payload = await asyncio.to_thread(_read_json_model, path, model)
            return cast(ModelT, payload)
        except (ValidationError, JSONDecodeError, ValueError) as exc:
            error_info = _build_artifact_payload_error_info(
                "load_artifact_json",
                metadata,
                path,
                self._backend,
                exc,
            )
            raise StorageError(error_info) from exc
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="load_artifact_json",
                        artifact_id=artifact_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    async def load_artifact_jsonl(
        self, artifact_id: ArtifactId, model: type[ModelT]
    ) -> list[ModelT]:
        """Load a JSONL artifact and parse into the provided model.

        Returns:
            list[ModelT]: Parsed artifact payloads.

        Raises:
            StorageError: If the artifact is missing or unreadable.
        """
        try:
            metadata = await asyncio.to_thread(
                _find_artifact_metadata, self._index_path, artifact_id
            )
        except (ValidationError, JSONDecodeError, ValueError) as exc:
            error_info = _build_record_parse_error_info(
                entity="Artifact index entry",
                operation="load_artifact_jsonl",
                artifact_id=artifact_id,
                path=self._index_path,
                backend=self._backend,
                exc=exc,
            )
            raise StorageError(error_info) from exc
        if metadata is None:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.NOT_FOUND,
                    message="Artifact not found",
                    details=StorageErrorDetails(
                        operation="load_artifact_jsonl",
                        artifact_id=artifact_id,
                        backend=self._backend,
                    ),
                )
            )
        if metadata.format != ArtifactFormat.JSONL:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.UNSUPPORTED_FORMAT,
                    message="Artifact is not JSONL",
                    details=StorageErrorDetails(
                        operation="load_artifact_jsonl",
                        artifact_id=artifact_id,
                        backend=self._backend,
                    ),
                )
            )
        path = _location_path(metadata)
        try:
            payload = await asyncio.to_thread(_read_jsonl_models, path, model)
            return cast(list[ModelT], payload)
        except (ValidationError, JSONDecodeError, ValueError) as exc:
            error_info = _build_artifact_payload_error_info(
                "load_artifact_jsonl",
                metadata,
                path,
                self._backend,
                exc,
            )
            raise StorageError(error_info) from exc
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="load_artifact_jsonl",
                        artifact_id=artifact_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    def _artifact_path(
        self, run_id: RunId, artifact_id: ArtifactId, format: ArtifactFormat
    ) -> Path:
        run_dir = self._base_dir / str(run_id)
        extension = format.value if isinstance(format, ArtifactFormat) else str(format)
        return run_dir / f"artifact-{artifact_id}.{extension}"

    def _with_location(
        self, metadata: ArtifactMetadata, path: Path
    ) -> ArtifactMetadata:
        location = StorageReference(backend=self._backend, path=str(path))
        return metadata.model_copy(update={"location": location})


class FileSystemLogStore(LogStoreProtocol):
    """Filesystem-backed JSONL log store."""

    def __init__(
        self,
        logs_dir: str,
        backend: StorageBackend = StorageBackend.FILESYSTEM,
    ) -> None:
        """Initialize the log store."""
        self._logs_dir = Path(logs_dir)
        self._backend = backend

    async def append_log(self, entry: LogEntry) -> None:
        """Append a single log entry.

        Raises:
            StorageError: If the log entry cannot be written.
        """
        path = self._log_path(entry.run_id)
        try:
            await asyncio.to_thread(_append_jsonl, path, entry, exclude_none=False)
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="append_log",
                        run_id=entry.run_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    async def append_logs(self, entries: list[LogEntry]) -> None:
        """Append multiple log entries for the same run.

        Raises:
            StorageError: If the log entries cannot be written.
        """
        if not entries:
            return
        run_ids = {entry.run_id for entry in entries}
        if len(run_ids) != 1:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.VALIDATION_ERROR,
                    message="Log entries must share a run_id",
                    details=StorageErrorDetails(
                        operation="append_logs",
                        backend=self._backend,
                        reason="mixed_run_ids",
                    ),
                )
            )
        run_id = next(iter(run_ids))
        path = self._log_path(run_id)
        try:
            await asyncio.to_thread(
                _append_jsonl_many, path, entries, exclude_none=False
            )
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="append_logs",
                        run_id=run_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    async def get_log_reference(self, run_id: RunId) -> LogFileReference | None:
        """Return the stored log file reference if present.

        Returns:
            LogFileReference | None: Log reference if the file exists.

        Raises:
            StorageError: If the log reference cannot be read.
        """
        path = self._log_path(run_id)
        if not await asyncio.to_thread(path.exists):
            return None
        try:
            return await asyncio.to_thread(
                _build_log_reference, path, run_id, self._backend
            )
        except OSError as exc:
            raise StorageError(
                StorageErrorInfo(
                    code=StorageErrorCode.IO_ERROR,
                    message=str(exc),
                    details=StorageErrorDetails(
                        operation="get_log_reference",
                        run_id=run_id,
                        backend=self._backend,
                        path=str(path),
                    ),
                )
            ) from exc

    def _log_path(self, run_id: RunId) -> Path:
        return self._logs_dir / f"{run_id}.jsonl"


def _write_json_file(path: Path, payload: BaseSchema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_json = payload.model_dump_json(exclude_none=True)
    path.write_text(payload_json, encoding="utf-8")


def _write_jsonl_file(path: Path, payload: Sequence[BaseSchema]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(
            item.model_dump_json(exclude_none=True) + "\n" for item in payload
        )


def _append_jsonl(
    path: Path, payload: BaseSchema, *, exclude_none: bool = True
) -> None:
    _append_jsonl_many(path, [payload], exclude_none=exclude_none)


def _append_jsonl_many(
    path: Path, payload: Sequence[BaseSchema], *, exclude_none: bool = True
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.writelines(
            item.model_dump_json(exclude_none=exclude_none) + "\n" for item in payload
        )


def _read_json_model(path: Path, model: _SchemaModel) -> BaseSchema:
    payload = path.read_text(encoding="utf-8")
    return model.model_validate_json(payload)


def _read_jsonl_models(path: Path, model: _SchemaModel) -> list[BaseSchema]:
    results: list[BaseSchema] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            results.append(model.model_validate_json(line))
    return results


def _read_run_index_records(index_dir: Path) -> list[RunIndexRecord]:
    records: list[RunIndexRecord] = []
    for path in index_dir.glob("*.json"):
        records.append(RunIndexRecord.model_validate_json(path.read_text("utf-8")))
    return records


def _read_artifacts_for_run(index_path: Path, run_id: RunId) -> list[ArtifactMetadata]:
    if not index_path.exists():
        return []
    artifacts: list[ArtifactMetadata] = []
    with open(index_path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            artifact = ArtifactMetadata.model_validate_json(line)
            if artifact.run_id == run_id:
                artifacts.append(artifact)
    return artifacts


def _find_artifact_metadata(
    index_path: Path, artifact_id: ArtifactId
) -> ArtifactMetadata | None:
    if not index_path.exists():
        return None
    found: ArtifactMetadata | None = None
    with open(index_path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            artifact = ArtifactMetadata.model_validate_json(line)
            if artifact.artifact_id == artifact_id:
                found = artifact
    return found


def _location_path(metadata: ArtifactMetadata) -> Path:
    if metadata.location.path is None:
        raise StorageError(
            StorageErrorInfo(
                code=StorageErrorCode.UNSUPPORTED_FORMAT,
                message="Artifact location does not include a filesystem path",
                details=StorageErrorDetails(
                    operation="load_artifact",
                    run_id=metadata.run_id,
                    artifact_id=metadata.artifact_id,
                    backend=metadata.location.backend,
                    uri=metadata.location.uri,
                ),
            )
        )
    return Path(metadata.location.path)


def _build_log_reference(
    path: Path,
    run_id: RunId,
    backend: StorageBackend,
) -> LogFileReference:
    stat = path.stat()
    created_at = _format_timestamp(stat.st_ctime)
    updated_at = _format_timestamp(stat.st_mtime)
    location = StorageReference(backend=backend, path=str(path))
    return LogFileReference(
        run_id=run_id,
        created_at=created_at,
        updated_at=updated_at,
        location=location,
        entry_count=None,
    )


def _format_timestamp(value: float) -> Timestamp:
    return datetime.fromtimestamp(value, UTC).isoformat()


def _read_run_state_record(path: Path) -> RunStateRecord:
    payload = path.read_text(encoding="utf-8")
    return RunStateRecord.model_validate_json(payload)


def _is_json_validation_error(exc: ValidationError) -> bool:
    for error in exc.errors():
        error_type = str(error.get("type", ""))
        if error_type.startswith("json_"):
            return True
    return False


def _build_record_parse_error_info(
    *,
    entity: str,
    operation: str,
    path: Path,
    backend: StorageBackend,
    exc: Exception,
    run_id: RunId | None = None,
    artifact_id: ArtifactId | None = None,
) -> StorageErrorInfo:
    code = StorageErrorCode.VALIDATION_ERROR
    message = f"{entity} failed schema validation"
    if isinstance(exc, ValidationError):
        if _is_json_validation_error(exc):
            code = StorageErrorCode.SERIALIZATION_ERROR
            message = f"{entity} JSON could not be parsed"
    elif isinstance(exc, (JSONDecodeError, ValueError)):
        code = StorageErrorCode.SERIALIZATION_ERROR
        message = f"{entity} JSON could not be parsed"
    return StorageErrorInfo(
        code=code,
        message=message,
        details=StorageErrorDetails(
            operation=operation,
            run_id=run_id,
            artifact_id=artifact_id,
            backend=backend,
            path=str(path),
            reason=str(exc),
        ),
    )


def _build_artifact_payload_error_info(
    operation: str,
    metadata: ArtifactMetadata,
    path: Path,
    backend: StorageBackend,
    exc: Exception,
) -> StorageErrorInfo:
    code = StorageErrorCode.VALIDATION_ERROR
    message = "Artifact payload failed schema validation"
    if isinstance(exc, ValidationError):
        if _is_json_validation_error(exc):
            code = StorageErrorCode.SERIALIZATION_ERROR
            message = "Artifact JSON could not be parsed"
    elif isinstance(exc, (JSONDecodeError, ValueError)):
        code = StorageErrorCode.SERIALIZATION_ERROR
        message = "Artifact JSON could not be parsed"
    return StorageErrorInfo(
        code=code,
        message=message,
        details=StorageErrorDetails(
            operation=operation,
            run_id=metadata.run_id,
            artifact_id=metadata.artifact_id,
            backend=backend,
            path=str(path),
            reason=str(exc),
        ),
    )
