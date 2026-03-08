# Phase Execution & Sharding Config Plan

## Goal
- Define per-phase execution strategies (full/scene/route) and concurrency controls that integrate with the orchestrator core and support future sharding-aware specs.
- Extend schemas to capture route-aware sharding while keeping existing chunk strategy intact for backward compatibility.
- Ensure shard planning is transparent in logs to support incremental rerun/diffing work later in the roadmap.

## Execution Note
- Execute Task 1 now, then continue with implementation tasks.

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals.

## Task 2: Schema updates for sharding configuration
- Add `ROUTE` to `PhaseWorkStrategy` and document execution semantics.
- Add `route_id` to `SourceLine` and `TranslatedLine` with a shared `RouteId` primitive.
- Extend `PhaseExecutionConfig` with `route_batch_size` and strategy-aware validation.

## Task 3: Orchestrator sharding logic + transparency
- Add route grouping helper and extend work chunking to support `ROUTE`.
- Validate route strategy requires route metadata (fail fast with structured errors).
- Emit shard plan metadata (strategy, shard count, parallel cap) in phase logs.

## Task 4: Tests (unit)
- Cover `ROUTE` strategy validation in config schema tests.
- Verify route sharding grouping and missing-route errors in orchestrator tests.

## Task 5: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass.
- Fix failures and re-run until green.

## References Studied
- `packages/rentl-schemas/src/rentl_schemas/config.py`
- `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- `packages/rentl-schemas/src/rentl_schemas/io.py`
- `packages/rentl-core/src/rentl_core/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- `agent-os/specs/2026-01-27-1036-pipeline-orchestrator-core/plan.md`

## Standards Applied
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- architecture/none-vs-empty
- architecture/naming-conventions
- ux/progress-is-product
- ux/trust-through-transparency
- testing/make-all-gate

## Product Alignment
- v0.1 requires a deterministic, phase-based pipeline with clear progress reporting.
- This spec keeps v0.1 working while enabling future multi-agent sharding and incremental reruns.
