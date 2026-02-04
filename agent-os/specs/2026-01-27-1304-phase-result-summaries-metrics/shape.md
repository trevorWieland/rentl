# Phase Result Summaries & Metrics — Shaping Notes

## Scope
Define and persist per-phase result summaries and metrics for v0.1 (glossary counts, QA totals, annotation coverage), emit summaries on phase completion, and keep the schema extensible for v0.2+ telemetry.

## Decisions
- Use roadmap scope for v0.1 metrics; no extra must-haves.
- Store summaries on `PhaseRunRecord` and include them in phase-completed logs.
- Add optional metric dimensions to support v0.2+ per-agent or per-shard summaries.
- Keep metrics numeric with strict keys/units; include `QaSummary` for QA detail.

## Context
- **Visuals:** None
- **References:** Orchestrator, storage ports, pipeline schemas, progress schemas, phase outputs
- **Product alignment:** v0.1 observability requirements with a bias toward v0.2+ telemetry extensibility

## Standards Applied
- testing/make-all-gate — Verification required before completion
- architecture/log-line-format — JSONL log payloads must be stable and structured
- architecture/none-vs-empty — Optional lists default to None; empty indicates computed empty
- architecture/naming-conventions — snake_case keys, PascalCase classes
- architecture/id-formats — UUIDv7 for internal identifiers
- python/async-first-design — Async APIs for I/O and persistence
- python/pydantic-only-schemas — Pydantic schemas with Field metadata
- python/strict-typing-enforcement — No Any; explicit types only
- ux/progress-is-product — Phase summaries must be visible and unambiguous
- ux/trust-through-transparency — Result metrics explain quality and changes
