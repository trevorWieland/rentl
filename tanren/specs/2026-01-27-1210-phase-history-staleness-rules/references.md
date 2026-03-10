# References for Phase History & Staleness Rules

## Similar Implementations

### Orchestrator phase history + staleness
- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Existing revision tracking, dependency capture, and stale invalidation logic
- **Key patterns:** `_next_revision`, `_build_dependencies`, `_update_stale_flags`, `_is_record_stale`

### Run state schema
- **Location:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- **Relevance:** `PhaseRunRecord`, `RunState`, and artifact lineage structures
- **Key patterns:** strict Field descriptions, optional history fields, dependency schema

### Primitives + ID formats
- **Location:** `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- **Relevance:** UUIDv7 IDs, phase enums, timestamp formats
- **Key patterns:** `PhaseRunId`, `RunId`, `PhaseName`

### Spec 01: Schema Definitions & Validation
- **Location:** `agent-os/specs/2026-01-25-1200-pydantic-schemas-validation/plan.md`
- **Relevance:** Schema structure and strict validation requirements
- **Key patterns:** Pydantic-only schemas, Field validation rules

### Spec 02: Progress Semantics & Tracking
- **Location:** `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/plan.md`
- **Relevance:** Progress and event visibility expectations for phase lifecycle updates
- **Key patterns:** progress emission at phase boundaries

### Spec 07: Pipeline Orchestrator Core
- **Location:** `agent-os/specs/2026-01-27-1036-pipeline-orchestrator-core/plan.md`
- **Relevance:** Orchestration contract and initial staleness tracking
- **Key patterns:** dependency gating, staleness behavior, artifact persistence rules
