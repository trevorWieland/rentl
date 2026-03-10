# Phase History & Staleness Rules Plan

## Goal
- Define phase history and revision semantics for v0.1 runs.
- Persist phase revisions so downstream staleness checks are durable.
- Emit clear invalidation signals when upstream changes invalidate outputs.
- Keep rules forward-compatible for v0.2 incremental rerun/diffing (spec 28).

## Execution Note
- Execute Task 1 now, then continue with implementation tasks.

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals.

## Task 2: Define phase history + revision semantics
- Specify that phase history records only completed outputs; failures remain in logs + run error state.
- Define revision increments only on successful output creation.
- Document dependency capture rules for each phase (global vs target-language).

## Task 3: Schema updates for persistent revisions
- Add `PhaseRevision` entries to persist `(phase, target_language, revision)` in `RunState`.
- Require `phase_run_id` on `PhaseRunRecord` (UUIDv7) and enforce uniqueness in validation.
- Align `dependencies` with None vs empty semantics (explicit empty list when computed).

## Task 4: Orchestrator updates for revision lineage
- Generate a `phase_run_id` for each completed phase record.
- Ensure dependencies are recorded consistently (including empty lists).
- Persist `phase_revisions` in run state with deterministic ordering.
- Keep invalidation logging on stale transitions (one-time per record).

## Task 5: Tests (unit)
- Add tests for invalidation log events on upstream reruns.
- Update run state/storage tests for `phase_revisions` and `phase_run_id` requirements.

## Task 6: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass.
- Fix failures and re-run until green.

## References Studied
- `packages/rentl-core/src/rentl_core/orchestrator.py`
- `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- `agent-os/specs/2026-01-25-1200-pydantic-schemas-validation/plan.md`
- `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/plan.md`
- `agent-os/specs/2026-01-27-1036-pipeline-orchestrator-core/plan.md`

## Standards Applied
- architecture/log-line-format
- architecture/id-formats
- architecture/none-vs-empty
- architecture/naming-conventions
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- ux/progress-is-product
- ux/trust-through-transparency
- testing/make-all-gate

## Product Alignment
- v0.1 requires deterministic phase execution with auditable outputs and clear staleness flags.
- Spec 28 (Incremental Rerun & Diffing) depends on durable phase history and revision lineage.
