# Signposts

## Task 3

- **Problem:** One error handling path still constructs `ErrorResponse` without required `exit_code`.
- **Evidence:** `services/rentl-cli/src/rentl_cli/main.py:339` has `ErrorResponse(code="validation_error", message=str(exc), details=None)` while `packages/rentl-schemas/src/rentl_schemas/responses.py:50` requires `exit_code: int`.
- **Evidence:** Repro command output:
  - `python - <<'PY' ... ErrorResponse(code='validation_error', message='x', details=None) ... PY`
  - `ValidationError: 1 validation error for ErrorResponse`
  - `exit_code Field required [type=missing, ...]`
- **Impact:** Any ValueError routed through this JSON export branch can fail during error construction and break the API error envelope contract.

## Task 4

- **Problem:** `status --json` FAILED/CANCELLED handling raises `typer.Exit` inside `try`, but the broad `except Exception` catches it and routes it through `_error_from_exception`, which is not safe for `Exit("")`.
- **Evidence:** Control flow at `services/rentl-cli/src/rentl_cli/main.py:629` (`raise typer.Exit(code=ExitCode.ORCHESTRATION_ERROR.value)`) is wrapped by `except Exception` at `services/rentl-cli/src/rentl_cli/main.py:635`, then `_error_from_exception` at `services/rentl-cli/src/rentl_cli/main.py:2204` builds `ErrorResponse(message=str(exc))`.
- **Evidence:** Repro output on commit `0f15e8a` with a FAILED status progress log:
  - `EXIT=1`
  - `ValidationError: 1 validation error for ErrorResponse`
  - `message String should have at least 1 character [type=string_too_short, input_value='', ...]`
- **Impact:** Instead of stable orchestration exit code `20`, the command can crash with exit `1`, violating CLI exit code guarantees for automation.

## Task 6

- **Problem:** Integration test scenarios for validation error (exit 11) and runtime error (exit 99) were using invalid CLI arguments (like `export --run-id`), which triggered Typer's argument validation (exit 2) before application logic ran.
- **Evidence:** Test failures at `make all`:
  - `test_validation_error_returns_exit_code_11`: AssertionError: Expected JSON response, got: (empty stdout)
  - `test_runtime_error_returns_exit_code_99`: AssertionError: Expected JSON response, got: (empty stdout)
  - Typer CLI errors like "No such option: --run-id" with exit code 2
- **Tried:**
  1. Using nonexistent files to trigger FileNotFoundError → wrapped as ValueError (exit 11)
  2. Using invalid format values → Typer argument validation error (exit 2)
  3. Using directory as output file → still wrapped as ValueError (exit 11)
- **Solution:**
  1. For validation error: Use `export` with valid CLI args but `--expected-line-count` mismatch to trigger ValueError in application logic
  2. For runtime error: Monkeypatch `_export_async` to raise KeyError (not ValueError, ConfigError, etc.) which reaches the generic Exception handler → exit 99
  3. Monkeypatching required because almost all errors in export flow are wrapped as ValueError
- **Files affected:** `tests/integration/cli/test_exit_codes.py`
