spec_id: s0.1.35
issue: https://github.com/trevorWieland/rentl/issues/35
version: v0.1

# Plan: CLI Exit Codes + Error Taxonomy

## Decision Record

The CLI currently uses binary exit codes (0/1) and scatters ~23 error codes across 4 domain modules plus CLI-specific handling. CI pipelines and scripts cannot branch on failure type. This spec introduces a central ExitCode enum with category-based integer ranges, a registry mapping every domain error code to an exit code, and consistent behavior across JSON and interactive modes.

Exit code ranges follow a category scheme:
- 0: Success
- 10-19: Client/input errors (config, validation)
- 20-29: Domain/processing errors (orchestration, ingest, export, storage)
- 30-39: External service errors (connection)
- 99: Unexpected runtime errors

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit and push spec artifacts on the issue branch

- [x] Task 2: Define ExitCode Enum and Error Taxonomy Registry
  - Create `packages/rentl-schemas/src/rentl_schemas/exit_codes.py`
  - Define `ExitCode(IntEnum)`: SUCCESS=0, CONFIG_ERROR=10, VALIDATION_ERROR=11, ORCHESTRATION_ERROR=20, INGEST_ERROR=21, EXPORT_ERROR=22, STORAGE_ERROR=23, CONNECTION_ERROR=30, RUNTIME_ERROR=99
  - Create error taxonomy registry: `ERROR_CODE_TO_EXIT_CODE: dict[str, ExitCode]` mapping every domain ErrorCode member and CLI-specific code string to its ExitCode
  - Add `resolve_exit_code(error_code: str) -> ExitCode` function with fallback to RUNTIME_ERROR
  - Add exhaustiveness unit test: import all domain ErrorCode enums, assert every member is in the registry
  - Unit tests in `tests/unit/schemas/test_exit_codes.py`: enum values correct, mapping complete, resolve function works for known and unknown codes

- [x] Task 3: Add Exit Code to ApiResponse Envelope
  - Add `exit_code: int` field to `ErrorResponse` in `packages/rentl-schemas/src/rentl_schemas/responses.py`
  - Update `ErrorInfo.to_error_response()` methods in domain ports (orchestrator, ingest, export, storage) to include exit_code via the registry
  - Update `_error_from_exception()` in `services/rentl-cli/src/rentl_cli/main.py` to populate exit_code from the registry
  - Unit tests: verify ErrorResponse serialization includes exit_code, verify domain error conversion includes correct exit_code
  - [x] Fix: Add missing `exit_code` population in JSON export `except ValueError` path at `services/rentl-cli/src/rentl_cli/main.py:339` (audit round 1)
  - [x] Fix: Add a unit/integration test that exercises the `services/rentl-cli/src/rentl_cli/main.py:339` branch and asserts error envelope includes non-null `exit_code` (audit round 1)

- [ ] Task 4: Replace Hardcoded Exit Codes in CLI
  - Replace all `typer.Exit(code=1)` in `main.py` with `typer.Exit(code=exit_code.value)` using the ExitCode enum
  - Make JSON mode return non-zero exit codes on error (remove the always-exit-0 behavior)
  - Ensure all error handling paths resolve exit codes through the centralized registry
  - Add a grep/ast-based unit test or lint check to verify no hardcoded integer exit codes remain in CLI code
  - Update any existing tests that assert `exit_code == 0` for JSON error responses to assert the correct non-zero code
  - [ ] Fix: In `status`, do not catch intentional `typer.Exit` from FAILED/CANCELLED branches; allow `ExitCode.ORCHESTRATION_ERROR` to propagate (currently swallowed by `except Exception` and remapped) at `services/rentl-cli/src/rentl_cli/main.py:629` and `services/rentl-cli/src/rentl_cli/main.py:635` (audit round 1)
  - [ ] Fix: Add regression test for `status --json` when run status is FAILED/CANCELLED asserting exit code `20` and a single JSON response envelope (currently returns exit `1` due `ValidationError`) around `services/rentl-cli/src/rentl_cli/main.py:636` and `_error_from_exception` at `services/rentl-cli/src/rentl_cli/main.py:2204` (audit round 1)

- [ ] Task 5: Integration Tests for Exit Code Scenarios
  - Create BDD feature file: `tests/integration/features/cli/exit_codes.feature`
  - Create step definitions: `tests/integration/cli/test_exit_codes.py`
  - Scenarios: success (exit 0), config error (exit 10), validation error (exit 11), runtime error (exit 99)
  - Verify JSON mode returns matching exit codes with exit_code field in error envelope
  - Verify interactive mode returns matching exit codes
  - Ensure all scenarios pass with `make all`
