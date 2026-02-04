# Log/Event Taxonomy & Sink Protocols Plan

## Goal
- Standardize run/phase event names and payloads for v0.1 observability
- Define sink protocols and adapters for logs/progress without coupling core to infrastructure
- Ensure logs and progress updates are consistent, queryable, and UX-ready

## Execution Note
- Execute Task 1 now, then continue with implementation tasks

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals

## Task 2: Define the v0.1 event taxonomy
- Inventory existing event names (run/phase/ingest/export/progress)
- Standardize naming conventions and suffixes across run/phase events
- Define required payload keys for each category (run_id, phase, revision, target_language, counts, error info)

## Task 3: Add event schemas/enums in `rentl-schemas`
- Introduce event enums/types for run/phase/progress operations
- Add typed payload models or helpers for `LogEntry.data` where appropriate
- Enforce `EventName` pattern compliance and update exports

## Task 4: Define sink protocols + adapters
- Keep `LogSinkProtocol` and `ProgressSinkProtocol` in core ports
- Add a progress sink adapter in `rentl-io` (filesystem/in-memory as needed)
- Provide a composite sink helper when multiple outputs are needed

## Task 5: Wire emission to taxonomy
- Update log builder helpers and orchestrator emission to use the canonical event names
- Align progress updates to new progress event names
- Ensure staleness invalidation and phase lifecycle events match the taxonomy

## Task 6: Tests (unit)
- Validate event enums, naming constraints, and payload schema validation
- Cover sink adapters and error paths
- Update existing tests to match standardized event names/payloads

## Task 7: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass
- Fix failures and re-run until green

## Deferred Follow-ups (Planned)
- **CLI wiring for status/telemetry sinks:** defer to spec 11 (CLI Workflow & Phase Selection)
- **Per-agent telemetry events:** defer to v0.2 specs (25)

## References Studied
- `packages/rentl-schemas/src/rentl_schemas/logs.py`
- `packages/rentl-schemas/src/rentl_schemas/progress.py`
- `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/ingest.py`
- `packages/rentl-core/src/rentl_core/ports/export.py`
- `packages/rentl-core/src/rentl_core/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/storage.py`
- `packages/rentl-io/src/rentl_io/storage/log_sink.py`
- `packages/rentl-io/src/rentl_io/storage/filesystem.py`
- `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/plan.md`
- `agent-os/specs/2026-01-26-1835-run-persistence-artifact-store/plan.md`
- `agent-os/specs/2026-01-26-1657-pipeline-orchestrator/plan.md`

## Standards Applied
- architecture/log-line-format
- architecture/adapter-interface-protocol
- architecture/thin-adapter-pattern
- architecture/id-formats
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- ux/progress-is-product
- ux/trust-through-transparency
- testing/make-all-gate

## Product Alignment
- v0.1 scope requires observability for every phase and status transition
- Logs and progress streams are foundational for CLI-first UX and trust
