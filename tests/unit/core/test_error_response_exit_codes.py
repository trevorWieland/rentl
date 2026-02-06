"""Unit tests verifying exit_code field in domain error responses."""

from rentl_core.ports.export import ExportErrorCode, ExportErrorInfo
from rentl_core.ports.ingest import IngestErrorCode, IngestErrorInfo
from rentl_core.ports.orchestrator import OrchestrationErrorCode, OrchestrationErrorInfo
from rentl_core.ports.storage import StorageErrorCode, StorageErrorInfo
from rentl_schemas.exit_codes import ExitCode


def test_orchestration_error_includes_exit_code() -> None:
    """Verify orchestration errors include correct exit code."""
    error_info = OrchestrationErrorInfo(
        code=OrchestrationErrorCode.MISSING_DEPENDENCY,
        message="Missing required phase",
    )
    error_response = error_info.to_error_response()
    assert error_response.exit_code == ExitCode.ORCHESTRATION_ERROR


def test_ingest_error_includes_exit_code() -> None:
    """Verify ingest errors include correct exit code."""
    error_info = IngestErrorInfo(
        code=IngestErrorCode.PARSE_ERROR,
        message="Failed to parse input",
    )
    error_response = error_info.to_error_response()
    assert error_response.exit_code == ExitCode.INGEST_ERROR


def test_export_error_includes_exit_code() -> None:
    """Verify export errors include correct exit code."""
    error_info = ExportErrorInfo(
        code=ExportErrorCode.IO_ERROR,
        message="Failed to write output",
    )
    error_response = error_info.to_error_response()
    assert error_response.exit_code == ExitCode.EXPORT_ERROR


def test_storage_error_includes_exit_code() -> None:
    """Verify storage errors include correct exit code."""
    error_info = StorageErrorInfo(
        code=StorageErrorCode.NOT_FOUND,
        message="Run not found",
    )
    error_response = error_info.to_error_response()
    assert error_response.exit_code == ExitCode.STORAGE_ERROR
