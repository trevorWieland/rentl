# Run Persistence & Artifact Store Protocols Plan

## Goal
- Define storage interfaces for durable run state, artifacts, and logs in v0.1
- Keep storage adapters swappable (filesystem today, PostgreSQL/S3 tomorrow)
- Ensure artifacts and logs are auditable, immutable JSONL where applicable

## Execution Note
- Execute Task 1 now, then continue with implementation tasks

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals

## Task 2: Define storage domain model
- Specify run state snapshot vs run index records and what must be persisted
- Define artifact taxonomy (phase outputs, intermediate JSONL, QA reports, exports)
- Define log file references and retention expectations
- Align path layout with project paths and forward-looking storage backends

## Task 3: Add storage schemas in `rentl-schemas`
- Add schema models for run summary/index, artifact metadata, and log references
- Keep optional list semantics aligned with none-vs-empty
- Export new schemas from `rentl_schemas/__init__.py`

## Task 4: Define storage protocols in `rentl-core`
- Add async protocols for run state persistence and artifact/log storage
- Define structured storage errors with {code, message, details}
- Ensure all storage access is via ports (no direct adapter access)

## Task 5: Implement filesystem adapters in `rentl-io`
- JSON file persistence for run state snapshots and run index
- JSONL artifact writer for per-phase outputs and logs
- Keep implementations async-first using `asyncio.to_thread`

## Task 6: Integrate persistence hooks
- Wire optional storage dependencies into orchestrator/log sinks
- Emit artifact references when phase outputs are persisted
- Keep orchestration logic independent of storage implementation

## Task 7: Tests (unit)
- Validate new schema models and serialization
- Validate filesystem adapters produce correct JSON/JSONL
- Cover error paths and none-vs-empty rules

## Task 8: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass
- Fix failures and re-run until green

## Deferred Follow-ups (Planned)
- **CLI wiring for persistence stores:** defer to spec 11 (CLI Workflow & Phase Selection)
- **PostgreSQL storage adapter:** defer to spec 30 (Adapter Interface Framework)
- **Per-phase artifact persistence policy:** defer to specs 07 (Pipeline Orchestrator Core), 10 (Phase Result Summaries & Metrics), and 06 (Log/Event Taxonomy)

## References Studied
- `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- `packages/rentl-schemas/src/rentl_schemas/logs.py`
- `packages/rentl-schemas/src/rentl_schemas/progress.py`
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/ingest.py`
- `packages/rentl-core/src/rentl_core/ports/export.py`
- `packages/rentl-io/src/rentl_io/export/jsonl_adapter.py`
- `agent-os/specs/2026-01-26-1657-pipeline-orchestrator/plan.md`

## Standards Applied
- architecture/adapter-interface-protocol
- architecture/thin-adapter-pattern
- architecture/log-line-format
- architecture/naming-conventions
- architecture/none-vs-empty
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- testing/make-all-gate

## Product Alignment
- v0.1 scope requires durable runs and auditability to support CLI observability
- Storage contracts must allow future adapters (SQLite/PostgreSQL, object stores)
