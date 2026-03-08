# Pipeline Orchestrator — Shaping Notes

## Scope

Implement the core orchestration layer that manages phase execution as flexible, user-addressable aspects of the workflow (ingest, context, pretranslation, translate, QA, edit, export). The orchestrator must support out-of-order reruns with dependency gating, track phase revisions and staleness, and emit clear progress/log events. It must also support multi-agent fan-out within phases with deterministic aggregation, while remaining compatible with v0.1 single-agent phases.

## Decisions

- Phases are not a rigid pipeline; users can jump or re-run phases as long as hard prerequisites are satisfied.
- Hard dependencies are enforced (e.g., ingest before others, translate before QA/edit/export); soft dependencies are optional but tracked when used.
- Phase executions record dependency lineage and revisions so downstream results can be marked stale after upstream changes.
- Multi-agent fan-out is part of the orchestration contract now, with deterministic merge semantics.
- Progress/log emission is first-class to ensure transparency and user trust.
- Design favors forward compatibility for v0.2+ multi-agent teams and v1.0 reliability requirements.

## Context

- **Visuals:** None
- **References:** `packages/rentl-schemas/src/rentl_schemas/`, `packages/rentl-core/src/rentl_core/ports/`, prior specs for schemas, progress, ingest/export
- **Product alignment:** Aligns to v0.1 playable patch workflow and mission emphasis on phase-based orchestration, BYOK flexibility, and observability, while keeping a forward-looking architecture for later releases.

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
