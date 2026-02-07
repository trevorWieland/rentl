"""Unit tests for CLI exit code taxonomy and registry."""

from rentl_core.ports.export import ExportErrorCode
from rentl_core.ports.ingest import IngestErrorCode
from rentl_core.ports.orchestrator import OrchestrationErrorCode
from rentl_core.ports.storage import StorageErrorCode
from rentl_schemas.exit_codes import (
    DOMAIN_PREFIXES,
    ERROR_CODE_TO_EXIT_CODE,
    ExitCode,
    resolve_exit_code,
)

# --- ExitCode enum value tests ---


def test_exit_code_success_is_zero() -> None:
    """Ensure SUCCESS maps to exit code 0."""
    assert ExitCode.SUCCESS == 0


def test_exit_code_config_error() -> None:
    """Ensure CONFIG_ERROR maps to exit code 10."""
    assert ExitCode.CONFIG_ERROR == 10


def test_exit_code_validation_error() -> None:
    """Ensure VALIDATION_ERROR maps to exit code 11."""
    assert ExitCode.VALIDATION_ERROR == 11


def test_exit_code_orchestration_error() -> None:
    """Ensure ORCHESTRATION_ERROR maps to exit code 20."""
    assert ExitCode.ORCHESTRATION_ERROR == 20


def test_exit_code_ingest_error() -> None:
    """Ensure INGEST_ERROR maps to exit code 21."""
    assert ExitCode.INGEST_ERROR == 21


def test_exit_code_export_error() -> None:
    """Ensure EXPORT_ERROR maps to exit code 22."""
    assert ExitCode.EXPORT_ERROR == 22


def test_exit_code_storage_error() -> None:
    """Ensure STORAGE_ERROR maps to exit code 23."""
    assert ExitCode.STORAGE_ERROR == 23


def test_exit_code_connection_error() -> None:
    """Ensure CONNECTION_ERROR maps to exit code 30."""
    assert ExitCode.CONNECTION_ERROR == 30


def test_exit_code_runtime_error() -> None:
    """Ensure RUNTIME_ERROR maps to exit code 99."""
    assert ExitCode.RUNTIME_ERROR == 99


def test_exit_code_member_count() -> None:
    """Ensure no members were accidentally added or removed."""
    assert len(ExitCode) == 9


def test_exit_code_is_int_enum() -> None:
    """ExitCode values can be used as plain ints."""
    assert isinstance(ExitCode.SUCCESS, int)
    assert ExitCode.SUCCESS + 1 == 1


# --- Registry exhaustiveness tests ---


def test_all_orchestration_codes_mapped() -> None:
    """Every OrchestrationErrorCode member is in the registry."""
    for member in OrchestrationErrorCode:
        key = f"orchestration.{member.value}"
        assert key in ERROR_CODE_TO_EXIT_CODE, (
            f"OrchestrationErrorCode.{member.name} ({key}) missing from registry"
        )
        assert ERROR_CODE_TO_EXIT_CODE[key] == ExitCode.ORCHESTRATION_ERROR


def test_all_ingest_codes_mapped() -> None:
    """Every IngestErrorCode member is in the registry."""
    for member in IngestErrorCode:
        key = f"ingest.{member.value}"
        assert key in ERROR_CODE_TO_EXIT_CODE, (
            f"IngestErrorCode.{member.name} ({key}) missing from registry"
        )
        assert ERROR_CODE_TO_EXIT_CODE[key] == ExitCode.INGEST_ERROR


def test_all_export_codes_mapped() -> None:
    """Every ExportErrorCode member is in the registry."""
    for member in ExportErrorCode:
        key = f"export.{member.value}"
        assert key in ERROR_CODE_TO_EXIT_CODE, (
            f"ExportErrorCode.{member.name} ({key}) missing from registry"
        )
        assert ERROR_CODE_TO_EXIT_CODE[key] == ExitCode.EXPORT_ERROR


def test_all_storage_codes_mapped() -> None:
    """Every StorageErrorCode member is in the registry."""
    for member in StorageErrorCode:
        key = f"storage.{member.value}"
        assert key in ERROR_CODE_TO_EXIT_CODE, (
            f"StorageErrorCode.{member.name} ({key}) missing from registry"
        )
        assert ERROR_CODE_TO_EXIT_CODE[key] == ExitCode.STORAGE_ERROR


def test_cli_level_codes_present() -> None:
    """CLI-specific error codes must be in the registry."""
    assert ERROR_CODE_TO_EXIT_CODE["config_error"] == ExitCode.CONFIG_ERROR
    assert ERROR_CODE_TO_EXIT_CODE["validation_error"] == ExitCode.VALIDATION_ERROR
    assert ERROR_CODE_TO_EXIT_CODE["runtime_error"] == ExitCode.RUNTIME_ERROR


def test_domain_prefix_coverage() -> None:
    """Every domain error enum class has a DOMAIN_PREFIXES entry."""
    expected_classes = {
        "OrchestrationErrorCode",
        "IngestErrorCode",
        "ExportErrorCode",
        "StorageErrorCode",
    }
    assert set(DOMAIN_PREFIXES.keys()) == expected_classes


def test_total_registry_entries() -> None:
    """Registry has 24 entries (3 CLI + 21 domain)."""
    assert len(ERROR_CODE_TO_EXIT_CODE) == 24


# --- resolve_exit_code tests ---


def test_resolve_cli_code_without_domain() -> None:
    """Resolve CLI codes without domain prefix."""
    assert resolve_exit_code("config_error") == ExitCode.CONFIG_ERROR


def test_resolve_cli_validation_error_without_domain() -> None:
    """Resolve validation_error without domain returns CLI code."""
    assert resolve_exit_code("validation_error") == ExitCode.VALIDATION_ERROR


def test_resolve_domain_qualified_ingest() -> None:
    """Domain-qualified lookup returns domain-specific exit code."""
    assert (
        resolve_exit_code("validation_error", domain="ingest") == ExitCode.INGEST_ERROR
    )


def test_resolve_domain_qualified_export() -> None:
    """Domain-qualified lookup for export io_error."""
    assert resolve_exit_code("io_error", domain="export") == ExitCode.EXPORT_ERROR


def test_resolve_domain_qualified_storage() -> None:
    """Domain-qualified lookup for storage not_found."""
    assert resolve_exit_code("not_found", domain="storage") == ExitCode.STORAGE_ERROR


def test_resolve_domain_qualified_orchestration() -> None:
    """Domain-qualified lookup for orchestration codes."""
    assert (
        resolve_exit_code("missing_dependency", domain="orchestration")
        == ExitCode.ORCHESTRATION_ERROR
    )


def test_resolve_unknown_code_returns_runtime_error() -> None:
    """Unknown error codes fall back to RUNTIME_ERROR."""
    assert resolve_exit_code("totally_unknown") == ExitCode.RUNTIME_ERROR


def test_resolve_unknown_domain_falls_back() -> None:
    """Unknown domain falls back to unqualified lookup."""
    assert (
        resolve_exit_code("config_error", domain="nonexistent") == ExitCode.CONFIG_ERROR
    )


def test_resolve_unknown_domain_and_code() -> None:
    """Unknown domain and code returns RUNTIME_ERROR."""
    assert (
        resolve_exit_code("unknown_code", domain="unknown_domain")
        == ExitCode.RUNTIME_ERROR
    )
