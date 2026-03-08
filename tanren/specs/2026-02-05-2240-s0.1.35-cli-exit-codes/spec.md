spec_id: s0.1.35
issue: https://github.com/trevorWieland/rentl/issues/35
version: v0.1

# Spec: CLI Exit Codes + Error Taxonomy

## Problem

The CLI returns exit code 0 or 1 for every outcome. CI pipelines and scripts cannot distinguish between a config error, a validation error, an orchestration failure, or an unexpected crash — they all look the same. This makes automated workflows fragile and debugging harder than it needs to be.

## Goals

- Define a stable, documented set of CLI exit codes that differentiate failure categories
- Consolidate the scattered domain error codes into a single importable error taxonomy registry
- Ensure both JSON and interactive output modes return consistent, meaningful exit codes
- Enable CI/scripting consumers to branch on exit codes reliably

## Non-Goals

- Changing the structure of domain-level error enums (OrchestrationErrorCode, IngestErrorCode, etc.) — they stay where they are
- Adding new domain error codes beyond what already exists
- Redesigning the ApiResponse envelope format — only adding an exit_code field
- User-facing error message improvements (that's a separate concern)

## Acceptance Criteria

- [ ] Central `ExitCode` enum exists with distinct integer codes for: success (0), config error, validation error, orchestration error, ingest error, export error, storage error, connection error, and unexpected runtime error
- [ ] Central error taxonomy module consolidates all error codes (domain + CLI-specific) into a single importable registry with documented categories and exit code mappings
- [ ] CLI commands use the `ExitCode` enum — all `typer.Exit()` calls reference the enum, not hardcoded integers
- [ ] JSON output includes exit code in the envelope — the `error` section of `ApiResponse` includes the exit code integer alongside the error code string
- [ ] JSON mode returns non-zero exit codes on error (matching interactive mode behavior)
- [ ] Unit tests verify enum completeness, mapping exhaustiveness, and error-to-exit-code conversion for all error types
- [ ] Integration tests (BDD) verify correct exit codes for success, config error, validation error, and runtime error scenarios
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Exit codes are stable integers defined in a single enum** — No hardcoded integer literals (`typer.Exit(code=1)`) anywhere in CLI code; all exit codes must reference the central `ExitCode` enum.
2. **Every domain error code maps to exactly one exit code** — The mapping must be exhaustive (all existing error codes covered) and deterministic (same error always produces the same exit code).
3. **JSON output mode preserves exit code behavior** — JSON mode must return the same exit codes as interactive mode (not always 0). The error code is also present in the JSON envelope for programmatic consumers.
4. **No existing test behavior broken** — All existing integration tests must continue to pass (or be updated to assert the new, correct exit codes).
