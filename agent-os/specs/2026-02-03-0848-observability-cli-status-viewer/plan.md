# Observability Surface (CLI Status Viewer) — Plan

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-03-0848-observability-cli-status-viewer/` with:
- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context)
- **standards.md** — Relevant standards that apply
- **references.md** — Pointers to reference implementations studied
- **visuals/** — Any mockups or screenshots provided (none)

## Task 2: Define observability telemetry schema additions

- Extend `rentl_schemas` with agent-level telemetry (agent id/name, phase, status,
  timestamps, and usage totals).
- Add a usage totals structure (input/output tokens, total tokens, request count)
  suitable for incremental updates.
- Define progress/log event names for agent start/progress/complete/fail aligned
  with `events.py`.
- Ensure schema validation and monotonic rules align with `progress.py`.

## Task 3: Emit agent/usage telemetry in core runtime

- Instrument agent execution in `rentl_agents.runtime.ProfileAgent` and/or
  `rentl_core.orchestrator` batching paths to emit agent lifecycle updates.
- Surface usage data from pydantic-ai responses where available.
- Emit telemetry through existing progress/log sinks (thin adapter rules).
- Ensure events are emitted on success, failure, and retry attempts.

## Task 4: Persist telemetry and add read model helpers

- Store agent updates in progress JSONL (or a parallel telemetry stream) and log
  JSONL with structured payloads.
- Add helpers to load/aggregate telemetry into a status snapshot (per-phase
  summary, agent status counts, token totals, ETA).
- Ensure compatibility with run state snapshots and progress files.

## Task 5: Implement CLI status viewer (`rentl status`)

- Add a CLI command that reads run state/log/progress data.
- Provide a snapshot view: phase status, percent, per-phase metrics, ETA, last
  update, completion summaries, token usage totals.
- Include agents running/completed counts.
- Accept `--run-id`, default to latest run when absent.
- Output JSON envelope (`ApiResponse`) plus a Rich-formatted view for humans.

## Task 6: Add live mode (`rentl status --watch`)

- Tail progress JSONL/telemetry and re-render on change.
- Show active phase, agents running, ETA, token usage growth.
- Handle completion/failure gracefully with final summary and exit code.

## Task 7: Tests

- Schema validation tests for new telemetry payloads.
- Emission tests in core runtime (event creation and sink calls).
- CLI status snapshot and watch modes using temp run state/progress files.
- Ensure existing CLI run-phase/run-pipeline tests still pass.

## Task 8: Verification - Run make all

Run `make all` to ensure all code passes quality checks:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests

This task MUST pass before the spec is considered complete. Failures must be
fixed and re-run until `make all` passes.

## Task 9: Verification - Manual CLI Run (sample_scenes.jsonl)

Run the CLI end-to-end against `sample_scenes.jsonl` and confirm:
- Progress tracking updates emit and render.
- Phase completion summaries appear.
- Run finishes cleanly (success or expected error).
- Log/progress artifacts are written.
