# References: CLI Exit Codes + Error Taxonomy

## Issue

- https://github.com/trevorWieland/rentl/issues/35

## Implementation Files

- `services/rentl-cli/src/rentl_cli/main.py` — CLI entrypoint, current exit code usage, `_error_from_exception()`
- `packages/rentl-schemas/src/rentl_schemas/responses.py` — ErrorResponse, ApiResponse schemas
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py` — OrchestrationErrorCode enum
- `packages/rentl-core/src/rentl_core/ports/ingest.py` — IngestErrorCode enum
- `packages/rentl-core/src/rentl_core/ports/export.py` — ExportErrorCode enum
- `packages/rentl-core/src/rentl_core/ports/storage.py` — StorageErrorCode enum

## New Files (to be created)

- `packages/rentl-schemas/src/rentl_schemas/exit_codes.py` — ExitCode enum + error taxonomy registry
- `tests/unit/schemas/test_exit_codes.py` — Unit tests for enum and registry
- `tests/integration/features/cli/exit_codes.feature` — BDD feature file
- `tests/integration/cli/test_exit_codes.py` — BDD step definitions

## Test Infrastructure

- `tests/integration/cli/` — Existing CLI integration tests
- `tests/integration/steps/cli_steps.py` — Shared CLI step definitions
- `tests/integration/conftest.py` — Test fixtures (cli_runner, fake_llm_runtime, etc.)

## Dependencies

- s0.1.06 — Core domain ports (where domain error enums live)
- s0.1.11 — CLI foundation (where exit code handling happens)
