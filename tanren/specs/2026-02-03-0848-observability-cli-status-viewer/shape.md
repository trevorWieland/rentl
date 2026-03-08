# Observability Surface (CLI Status Viewer) — Shaping Notes

## Scope

Deliver a CLI status viewer that shows live phase status, completion summaries,
agents running, ETA, and token usage. Add telemetry in core/runtime so CLI can
render agent-level progress and usage details, with a `status --watch` live mode
and a snapshot mode for audits.

## Decisions

- Include new telemetry for per-agent status and token usage in v0.1.
- Use a single `rentl status` command with `--watch` for live updates.
- Keep CLI as a thin adapter; core emits structured telemetry via progress/log
  sinks.
- Use JSONL progress/log files as the primary read model for status rendering.
- Enforce strict agent IO alignment globally: any agent receiving IDs must return
  exactly those IDs (no extras/omissions/duplicates), with per-chunk retries on
  mismatch.
- Treat alignment enforcement as a correctness gate, distinct from QA quality
  signals (e.g., untranslated line detection).

## Context

- **Visuals:** None
- **References:**
  - `services/rentl-cli/src/rentl_cli/main.py`
  - `packages/rentl-core/src/rentl_core/orchestrator.py`
  - `packages/rentl-schemas/src/rentl_schemas/progress.py`
  - `packages/rentl-schemas/src/rentl_schemas/events.py`
  - `packages/rentl-io/src/rentl_io/storage/progress_sink.py`
  - `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
  - `packages/rentl-schemas/src/rentl_schemas/results.py`
  - `services/rentl-tui/src/rentl_tui/app.py`
- **Product alignment:** Observability is a core differentiator; CLI is the
  primary surface; progress events and logs are structured JSONL; trust and
  transparency are required.

## Standards Applied

- testing/make-all-gate — Verification required before completion.
- ux/progress-is-product — Phase status and QA visibility must be immediate and
  unambiguous.
- ux/trust-through-transparency — No silent stalls; all errors/status must be
  visible.
- architecture/thin-adapter-pattern — CLI must remain a thin adapter.
- architecture/log-line-format — Structured JSONL log schema for events.
- architecture/api-response-format — CLI JSON responses use `{data, error, meta}`.
