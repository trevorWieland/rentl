# Log/Event Taxonomy & Sink Protocols — Shaping Notes

## Scope
- Standardize run/phase/ingest/export/progress event names and payloads for v0.1
- Define sink protocols and adapters for logs and progress without coupling core to infrastructure
- Ensure JSONL log lines and progress updates are consistent and UX-ready

## Decisions
- Use snake_case event names that align with `EventName` and `log-line-format`
- Consolidate phase lifecycle event naming with canonical suffixes
- Add or formalize progress sink adapters in `rentl-io`
- Keep core orchestration logic independent of sink implementations

## Context
- **Visuals:** None
- **References:**
  - `packages/rentl-schemas/src/rentl_schemas/logs.py`
  - `packages/rentl-schemas/src/rentl_schemas/progress.py`
  - `packages/rentl-schemas/src/rentl_schemas/primitives.py`
  - `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
  - `packages/rentl-core/src/rentl_core/ports/ingest.py`
  - `packages/rentl-core/src/rentl_core/ports/export.py`
  - `packages/rentl-core/src/rentl_core/orchestrator.py`
  - `packages/rentl-core/src/rentl_core/ports/storage.py`
  - `packages/rentl-io/src/rentl_io/storage/log_sink.py`
  - `packages/rentl-io/src/rentl_io/storage/filesystem.py`
  - `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/plan.md`
  - `agent-os/specs/2026-01-26-1835-run-persistence-artifact-store/plan.md`
  - `agent-os/specs/2026-01-26-1657-pipeline-orchestrator/plan.md`
- **Product alignment:** v0.1 observability and progress visibility are core UX requirements

## Standards Applied
- testing/make-all-gate — Verification required before completion
- architecture/log-line-format — JSONL log schema with required fields
- architecture/adapter-interface-protocol — access sinks via core protocols
- architecture/thin-adapter-pattern — CLI/TUI remain thin
- architecture/id-formats — UUIDv7 run IDs and stable identifiers
- python/pydantic-only-schemas — schemas are Pydantic models only
- python/strict-typing-enforcement — no Any/object in schemas
- ux/progress-is-product — progress events must be immediate/clear
- ux/trust-through-transparency — no silent failures or stalls
