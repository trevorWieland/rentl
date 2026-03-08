# Run Persistence & Artifact Store Protocols — Shaping Notes

## Scope

Define storage interfaces and schemas to persist run state, artifacts, and logs for the v0.1 pipeline. Provide filesystem adapters now while keeping protocols forward-compatible with enterprise storage backends (PostgreSQL, object stores) via the adapter interface pattern.

## Decisions

- Use protocol-based ports for run state, artifacts, and logs; adapters live in infrastructure packages.
- Persist immutable artifacts as JSONL where applicable; single snapshots use JSON.
- Separate run state snapshots from run index/summary records for faster listing.
- Ensure schemas and logs are fully typed and auditable; no secrets in artifacts/logs.
- Defer CLI wiring (spec 11), Postgres adapter (spec 30), and per-phase persistence policy (specs 06/07/10).

## Context

- **Visuals:** None
- **References:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`, `packages/rentl-core/src/rentl_core/ports/orchestrator.py`, `packages/rentl-io/src/rentl_io/export/jsonl_adapter.py`, `agent-os/specs/2026-01-26-1657-pipeline-orchestrator/plan.md`
- **Product alignment:** v0.1 needs durable runs and auditability to support CLI-first observability; storage must be swappable for enterprise backends.

## Standards Applied

- architecture/adapter-interface-protocol — storage access via ports only
- architecture/thin-adapter-pattern — persistence logic stays in core domain
- architecture/log-line-format — JSONL log schema
- architecture/naming-conventions — snake_case fields, PascalCase schemas
- architecture/none-vs-empty — optional lists use None vs [] semantics
- python/async-first-design — async I/O for persistence
- python/pydantic-only-schemas — pydantic models only
- python/strict-typing-enforcement — no Any/object
- testing/make-all-gate — run `make all` before completion
