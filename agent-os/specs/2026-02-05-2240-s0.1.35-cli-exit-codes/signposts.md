# Signposts

## Task 3

- **Problem:** One error handling path still constructs `ErrorResponse` without required `exit_code`.
- **Evidence:** `services/rentl-cli/src/rentl_cli/main.py:339` has `ErrorResponse(code="validation_error", message=str(exc), details=None)` while `packages/rentl-schemas/src/rentl_schemas/responses.py:50` requires `exit_code: int`.
- **Evidence:** Repro command output:
  - `python - <<'PY' ... ErrorResponse(code='validation_error', message='x', details=None) ... PY`
  - `ValidationError: 1 validation error for ErrorResponse`
  - `exit_code Field required [type=missing, ...]`
- **Impact:** Any ValueError routed through this JSON export branch can fail during error construction and break the API error envelope contract.
