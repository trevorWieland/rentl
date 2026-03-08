# Phase Result Summaries & Metrics Plan

## Goal
- Capture per-phase result summaries/metrics (glossary counts, QA totals, annotation coverage) for v0.1.
- Persist summaries per phase and target language alongside phase history for auditability and CLI status.
- Emit summaries in phase-completed logs to support observability and trust.
- Keep summary schema extensible for v0.2+ per-agent/per-shard metrics.

## Execution Note
- Execute Task 1 now, then continue with implementation tasks.

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals.

## Task 2: Define result summary semantics and metric catalog
- Define a v0.1 metric catalog per phase with strict keys, units, and descriptions.
- Establish how coverage metrics are computed (e.g., annotated lines / total lines).
- Clarify how optional inputs affect summary presence (None vs empty lists).
- Add an extensibility hook for v0.2+ (dimensions for agent/shard/segment).

## Task 3: Schema updates for phase result summaries
- Add `PhaseResultMetric`, `PhaseResultSummary`, and supporting enums/validators.
- Attach summary to `PhaseRunRecord` for durable history.
- Export new schemas from `rentl_schemas/__init__.py`.

## Task 4: Orchestrator summary computation + persistence
- Compute summary metrics per phase from phase outputs and source inputs.
- Attach summary to phase run records and persist in run state.
- Ensure summaries are scoped by target language for language phases.

## Task 5: Observability integration
- Include summary payloads in phase-completed log data.
- Keep summary payloads JSONL-safe and aligned with the log-line format.

## Task 6: Tests (unit)
- Validate metric definitions (keys, units, coverage math, uniqueness).
- Verify orchestrator summary computation and persistence per phase.
- Ensure log payloads include summary data on completion.

## Task 7: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass.
- Fix failures and re-run until green.

## References Studied
- `packages/rentl-core/src/rentl_core/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/storage.py`
- `packages/rentl-core/src/rentl_core/ports/export.py`
- `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- `packages/rentl-schemas/src/rentl_schemas/progress.py`
- `packages/rentl-schemas/src/rentl_schemas/phases.py`
- `packages/rentl-schemas/src/rentl_schemas/qa.py`
- `packages/rentl-schemas/src/rentl_schemas/events.py`
- `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- `agent-os/specs/2026-01-27-1210-phase-history-staleness-rules/plan.md`
- `agent-os/specs/2026-01-27-1128-phase-execution-sharding-config/plan.md`
- `agent-os/specs/2026-01-27-1036-pipeline-orchestrator-core/plan.md`

## Standards Applied
- architecture/log-line-format
- architecture/none-vs-empty
- architecture/naming-conventions
- architecture/id-formats
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- ux/progress-is-product
- ux/trust-through-transparency
- testing/make-all-gate

## Product Alignment
- v0.1 requires deterministic phase execution with clear quality signals per phase.
- CLI-first observability (spec 11) relies on trustworthy phase summaries.
- v0.2+ multi-agent telemetry can extend summaries via dimensions without breaking v0.1.
