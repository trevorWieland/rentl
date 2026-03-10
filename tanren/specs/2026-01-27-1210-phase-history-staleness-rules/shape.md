# Phase History & Staleness Rules — Shaping Notes

## Scope

Define how phase outputs are recorded, revisioned, and invalidated when upstream phases change. The rules must preserve v0.1 determinism, surface invalidation via logs, and keep lineage data durable for later incremental reruns.

## Decisions

- Phase history records completed outputs only; failures remain in logs and `RunState.last_error`.
- Revisions increment only when an output is successfully produced and persisted.
- Dependencies are captured per phase run, with explicit empty lists when no dependencies apply.
- Staleness is computed by comparing dependency revisions to latest revisions; outputs are flagged stale but not blocked in v0.1.
- Phase revisions are persisted as explicit `(phase, target_language, revision)` entries for durability and future diffing (spec 28).

## Context

- **Visuals:** None
- **References:** `packages/rentl-core/src/rentl_core/orchestrator.py`, `packages/rentl-schemas/src/rentl_schemas/pipeline.py`, spec 01/02/07 plans
- **Product alignment:** v0.1 playable patch goals; supports forward dependency for spec 28 incremental rerun/diffing.

## Standards Applied

- testing/make-all-gate — Verification required before completion
- architecture/log-line-format — Invalidation events emitted via JSONL logs
- architecture/id-formats — Phase run IDs use UUIDv7
- architecture/none-vs-empty — Dependencies recorded as empty lists when computed
- architecture/naming-conventions — Consistent naming for new schema fields
- python/async-first-design — Async orchestration paths remain non-blocking
- python/pydantic-only-schemas — All schema updates use Pydantic models
- python/strict-typing-enforcement — No Any/object; Field metadata required
- ux/progress-is-product — Invalidation visibility preserves trust
- ux/trust-through-transparency — Stale outputs are explicitly surfaced
