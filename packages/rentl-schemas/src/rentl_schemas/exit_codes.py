"""CLI exit code taxonomy and error-to-exit-code registry.

Defines a central ExitCode enum with category-based integer ranges and a
registry mapping every domain error code to its corresponding exit code.

Exit code ranges:
- 0: Success
- 10-19: Client/input errors (config, validation)
- 20-29: Domain/processing errors (orchestration, ingest, export, storage)
- 30-39: External service errors (connection)
- 99: Unexpected runtime errors
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """CLI exit codes by failure category."""

    SUCCESS = 0
    CONFIG_ERROR = 10
    VALIDATION_ERROR = 11
    ORCHESTRATION_ERROR = 20
    INGEST_ERROR = 21
    EXPORT_ERROR = 22
    STORAGE_ERROR = 23
    CONNECTION_ERROR = 30
    RUNTIME_ERROR = 99


# ---------------------------------------------------------------------------
# Error taxonomy registry
#
# Maps every known error code string to its ExitCode.
#
# Domain error codes are qualified with a domain prefix to avoid collisions
# (e.g. "ingest.validation_error" vs "export.validation_error").
# CLI-level codes (config_error, validation_error, runtime_error) are stored
# without a prefix for direct lookup.
# ---------------------------------------------------------------------------

ERROR_CODE_TO_EXIT_CODE: dict[str, ExitCode] = {
    # --- CLI-level codes (no prefix) ---
    "config_error": ExitCode.CONFIG_ERROR,
    "validation_error": ExitCode.VALIDATION_ERROR,
    "runtime_error": ExitCode.RUNTIME_ERROR,
    # --- Orchestration domain ---
    "orchestration.missing_dependency": ExitCode.ORCHESTRATION_ERROR,
    "orchestration.phase_not_configured": ExitCode.ORCHESTRATION_ERROR,
    "orchestration.phase_disabled": ExitCode.ORCHESTRATION_ERROR,
    "orchestration.invalid_state": ExitCode.ORCHESTRATION_ERROR,
    "orchestration.phase_execution_failed": ExitCode.ORCHESTRATION_ERROR,
    # --- Ingest domain ---
    "ingest.invalid_format": ExitCode.INGEST_ERROR,
    "ingest.parse_error": ExitCode.INGEST_ERROR,
    "ingest.missing_field": ExitCode.INGEST_ERROR,
    "ingest.validation_error": ExitCode.INGEST_ERROR,
    "ingest.io_error": ExitCode.INGEST_ERROR,
    # --- Export domain ---
    "export.invalid_format": ExitCode.EXPORT_ERROR,
    "export.validation_error": ExitCode.EXPORT_ERROR,
    "export.io_error": ExitCode.EXPORT_ERROR,
    "export.untranslated_text": ExitCode.EXPORT_ERROR,
    "export.dropped_column": ExitCode.EXPORT_ERROR,
    # --- Storage domain ---
    "storage.not_found": ExitCode.STORAGE_ERROR,
    "storage.io_error": ExitCode.STORAGE_ERROR,
    "storage.serialization_error": ExitCode.STORAGE_ERROR,
    "storage.validation_error": ExitCode.STORAGE_ERROR,
    "storage.conflict": ExitCode.STORAGE_ERROR,
    "storage.unsupported_format": ExitCode.STORAGE_ERROR,
}

# Domain prefix for each error code enum (used by resolve_exit_code).
DOMAIN_PREFIXES: dict[str, str] = {
    "OrchestrationErrorCode": "orchestration",
    "IngestErrorCode": "ingest",
    "ExportErrorCode": "export",
    "StorageErrorCode": "storage",
}


def resolve_exit_code(
    error_code: str, *, domain: str | None = None
) -> ExitCode:
    """Resolve an error code string to its ExitCode.

    Args:
        error_code: The error code string (e.g. "validation_error",
            "missing_dependency").
        domain: Optional domain prefix (e.g. "orchestration", "ingest").
            When provided, the lookup uses ``"{domain}.{error_code}"``
            first, falling back to an unqualified lookup.

    Returns:
        The matching ExitCode, or RUNTIME_ERROR if no mapping is found.
    """
    if domain:
        qualified = f"{domain}.{error_code}"
        if qualified in ERROR_CODE_TO_EXIT_CODE:
            return ERROR_CODE_TO_EXIT_CODE[qualified]

    if error_code in ERROR_CODE_TO_EXIT_CODE:
        return ERROR_CODE_TO_EXIT_CODE[error_code]

    return ExitCode.RUNTIME_ERROR
