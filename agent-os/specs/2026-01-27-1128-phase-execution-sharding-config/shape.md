# Phase Execution & Sharding Config — Shaping Notes

## Scope

Define per-phase execution strategies (full/scene/route) and concurrency controls for the pipeline, aligned with the orchestrator core. Extend schemas so sharding configuration is explicit and validated, and ensure route-based sharding is supported with deterministic grouping and transparent logging.

## Decisions

- Keep existing `chunk` strategy for backwards compatibility while adding `route` as a first-class strategy.
- Require `route_id` metadata on all source lines when `route` strategy is selected; fail fast otherwise.
- Record shard planning metadata in phase logs (strategy, shard count, parallel cap) to support future incremental rerun/diffing work.

## Context

- **Visuals:** None
- **References:** `packages/rentl-schemas/src/rentl_schemas/config.py`, `packages/rentl-schemas/src/rentl_schemas/primitives.py`, `packages/rentl-schemas/src/rentl_schemas/io.py`, `packages/rentl-core/src/rentl_core/orchestrator.py`, spec 07 plan.
- **Product alignment:** Supports v0.1 deterministic pipeline while enabling v0.2+ sharding-aware orchestration.

## Standards Applied

- testing/make-all-gate — Verification required before completion
- python/async-first-design — Async orchestration and agent execution
- python/pydantic-only-schemas — All new schemas use Pydantic
- python/strict-typing-enforcement — No Any/object usage
- architecture/none-vs-empty — Optional list semantics in new schemas
- architecture/naming-conventions — Consistent names for new fields
- ux/progress-is-product — Shard/phase status remains visible
- ux/trust-through-transparency — Explicit errors for missing route metadata
