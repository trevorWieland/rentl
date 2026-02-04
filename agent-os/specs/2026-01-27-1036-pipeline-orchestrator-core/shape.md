# Pipeline Orchestrator Core — Shaping Notes

## Scope

Rework the pipeline orchestrator core to align with spec 07 and v0.1 requirements, while biasing the design toward v0.2+ multi-agent orchestration. The orchestrator must enforce hard dependencies, support soft dependencies, track phase revisions and staleness, emit clear progress/log events, and persist artifacts deterministically.

## Decisions

- The orchestration contract explicitly defines hard vs soft prerequisites and blocked behavior before execution starts.
- Phase outputs record dependency lineage and revisions to support staleness invalidation and future diffing.
- Artifact persistence policy is defined in the orchestrator (not left implicit), aligned with storage protocols.
- Progress and log emission are first-class, covering run-level events and phase lifecycle events (including blocked/invalidated).
- Design is forward-compatible with v0.2 multi-agent teams and sharding while keeping v0.1 single-agent flows intact.

## Context

- **Visuals:** None
- **References:** `packages/rentl-core/src/rentl_core/orchestrator.py`, `packages/rentl-core/src/rentl_core/ports/`, `packages/rentl-schemas/src/rentl_schemas/`, related v0.1 spec plans for progress, persistence, and log taxonomy.
- **Product alignment:** Aligns to v0.1 playable patch goals but intentionally biases toward v0.2+ orchestration capabilities.

## Standards Applied

- testing/make-all-gate — Verification required before completion
- architecture/adapter-interface-protocol — Orchestrator depends on protocols, not adapters
- architecture/log-line-format — JSONL log events for run/phase state changes
- architecture/naming-conventions — Consistent naming across new APIs and schemas
- architecture/none-vs-empty — Optional list semantics in new schemas
- architecture/thin-adapter-pattern — Core orchestration remains in rentl-core
- python/async-first-design — Async orchestration and agent execution
- python/pydantic-only-schemas — All new schemas use Pydantic
- python/strict-typing-enforcement — No Any/object usage
- ux/progress-is-product — Progress emitted at run/phase milestones
- ux/speed-with-guardrails — Fast iterations with determinism and guardrails
- ux/trust-through-transparency — Visible errors, retries, and status
