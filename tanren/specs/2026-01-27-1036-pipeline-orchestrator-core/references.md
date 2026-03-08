# References for Pipeline Orchestrator Core

## Similar Implementations

### Core orchestrator
- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Current orchestration behavior, phase execution, progress updates, artifact persistence.
- **Key patterns:** Phase execution flow, deterministic merges, staleness invalidation logic.

### Orchestrator ports
- **Location:** `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- **Relevance:** Protocols for agent pools, log/progress sinks, error definitions.
- **Key patterns:** Async protocol interfaces and log builder helpers.

### Pipeline state and progress schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`, `packages/rentl-schemas/src/rentl_schemas/progress.py`
- **Relevance:** Run state, phase history, staleness flags, progress summaries.
- **Key patterns:** Run/phase metadata, progress aggregation, optional list semantics.

### Event taxonomy
- **Location:** `packages/rentl-schemas/src/rentl_schemas/events.py`
- **Relevance:** Canonical run/phase/progress event names and payloads.
- **Key patterns:** Phase lifecycle suffixes, progress event names.

### Orchestrator tests
- **Location:** `tests/unit/core/test_orchestrator.py`
- **Relevance:** Current dependency gating and staleness behavior tests.
- **Key patterns:** Minimal stub agents and adapters for unit tests.

## Spec Context

### Progress semantics
- **Location:** `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/plan.md`
- **Relevance:** Progress invariants and schema expectations used by orchestration.

### Run persistence + artifact store
- **Location:** `agent-os/specs/2026-01-26-1835-run-persistence-artifact-store/plan.md`
- **Relevance:** Storage protocols and persistence hooks that orchestration must invoke.

### Log/event taxonomy
- **Location:** `agent-os/specs/2026-01-26-2206-log-event-taxonomy-sinks/plan.md`
- **Relevance:** Canonical event names and sink expectations for observability.
