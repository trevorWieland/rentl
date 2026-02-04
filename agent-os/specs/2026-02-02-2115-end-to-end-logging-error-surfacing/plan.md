# End-to-End Logging & Error Surfacing — Plan

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-02-2115-end-to-end-logging-error-surfacing/` with:
- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context from our conversation)
- **standards.md** — Relevant standards that apply to this work
- **references.md** — Pointers to reference implementations studied
- **visuals/** — Any mockups or screenshots provided

## Task 2: Logging Config + Event Schema

- Add logging config to `RunConfig` that requires at least one sink.
- Define sink types (console, file, no-op) with strict Pydantic schemas and validation.
- Add event taxonomy for command-level logging (CLI command started/completed/failed) and keep event names snake_case.
- Update `rentl.toml` and `rentl.toml.example` with explicit log sink configuration.

## Task 3: Log Sink Adapters + Builders

- Implement `ConsoleLogSink` and `NoopLogSink` (JSONL output for console).
- Preserve `StorageLogSink` and `CompositeLogSink`; add a builder to map config to sink(s).
- Ensure no lazy imports; avoid circular dependencies by keeping adapters in `rentl-io`.

## Task 4: Core Enforcement + Phase Logs

- Make `PipelineOrchestrator` require a `LogSinkProtocol` (no `None`), update call sites/tests.
- Emit ingest/export started/completed/failed logs using existing builders in `rentl_core.ports.ingest` and `rentl_core.ports.export`.
- Ensure phase/run failures include `error_code`, `why`, and `next_action` in log payloads.

## Task 5: CLI Wiring + Actionable Errors

- Wire log sink creation in CLI based on config and add command-level logs for:
  - `validate-connection`
  - `export`
  - `run-pipeline`
  - `run-phase`
- Ensure CLI error responses remain `{data, error, meta}` and match error code conventions.
- Enforce redaction/no-API-key logging in command logs.

## Task 6: Tests + Fixtures

- Update unit/integration tests to include mandatory log sinks.
- Add coverage for console/no-op sinks and command-level logging events.
- Update config fixtures to pass validation with required sinks.

## Task 7: Verification - Run make all

Run `make all` to ensure all code passes quality checks:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests

This task MUST pass before the spec is considered complete. Failures must be fixed and re-run until `make all` passes.
