# Pipeline Orchestrator Plan

## Goal
- Provide flexible, phase-aware orchestration for the v0.1 pipeline with deterministic handoffs
- Support iterative phase runs (jumping forward/back) with dependency tracking and staleness signals
- Enable multi-agent fan-out within phases with deterministic aggregation, while keeping v0.1 single-agent compatible

## Execution Note
- Execute Task 1 now, then continue with implementation tasks

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals

## Task 2: Define orchestration contracts and dependency model
- Specify hard vs soft phase prerequisites and when phases are blocked
- Define phase execution model that supports N agents per phase (unique agents or clones) and shardable work units
- Define deterministic aggregation rules per phase (lines/scenes/issues) and conflict handling
- Add schemas for phase dependency lineage, revisioning, and staleness markers

## Task 3: Extend run state and progress semantics for iterative flows
- Add phase run history records with revisions, dependencies, target language, and staleness
- Keep progress reporting valid when phases are re-run out of order

## Task 4: Add core ports for phase agents and event/progress sinks
- Define async protocols for phase agents and agent pools (batch execution order guaranteed)
- Add async log/progress sink protocols and helpers for run/phase events

## Task 5: Implement the Pipeline Orchestrator core
- Implement run creation, run_phase, and run_plan orchestration in rentl-core
- Compose phase inputs from the latest artifacts and support optional dependency inputs
- Fan-out phase work across multiple agents with concurrency control and deterministic merges
- Track phase revisions, update run history, and mark downstream results stale on upstream changes
- Keep multi-language runs forward-compatible without assuming a single target language

## Task 6: Logging and progress emission helpers
- Emit run/phase start, completion, blocked, invalidated, and failure events aligned to JSONL log schema
- Emit progress updates for phase status transitions using progress schemas

## Task 7: Tests (unit)
- Validate new config and pipeline schemas
- Cover dependency gating, staleness invalidation, and multi-agent aggregation ordering
- Ensure progress/log helpers emit schema-valid payloads

## Task 8: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass
- Fix failures and re-run until green

## References Studied
- `packages/rentl-schemas/src/rentl_schemas/phases.py`
- `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- `packages/rentl-schemas/src/rentl_schemas/progress.py`
- `packages/rentl-schemas/src/rentl_schemas/config.py`
- `packages/rentl-schemas/src/rentl_schemas/logs.py`
- `packages/rentl-core/src/rentl_core/ports/ingest.py`
- `packages/rentl-core/src/rentl_core/ports/export.py`
- `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/`
- `agent-os/specs/2026-01-26-1223-import-adapter/`
- `agent-os/specs/2026-01-26-1449-export-adapter/`

## Standards Applied
- architecture/adapter-interface-protocol
- architecture/log-line-format
- architecture/naming-conventions
- architecture/none-vs-empty
- architecture/thin-adapter-pattern
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- testing/make-all-gate
- ux/progress-is-product
- ux/speed-with-guardrails
- ux/trust-through-transparency

## Product Alignment
- v0.1 scope requires a deterministic 5-phase pipeline with CLI-first workflow and strong observability
- Orchestration design is forward-looking for v0.2 multi-agent teams and v1.0 reliability
