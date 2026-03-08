# References for Phase Execution & Sharding Config

## Similar Implementations

### Orchestrator sharding + execution hooks
- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Existing phase execution flow, work chunking, and agent pool scheduling
- **Key patterns:** `_build_work_chunks`, `_run_agent_pool`, phase progress/log emission

### Execution config schema
- **Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`
- **Relevance:** `PhaseExecutionConfig` and validator logic for sharding strategies
- **Key patterns:** strategy-specific validation, PhaseConfig execution overrides

### Primitive enums + identifiers
- **Location:** `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- **Relevance:** `PhaseWorkStrategy` enum, shared ID type definitions
- **Key patterns:** StrEnum primitives, shared ID aliases

### IO schemas for line metadata
- **Location:** `packages/rentl-schemas/src/rentl_schemas/io.py`
- **Relevance:** `SourceLine` and `TranslatedLine` metadata fields
- **Key patterns:** optional identifiers and metadata propagation

### Orchestrator spec (spec 07)
- **Location:** `agent-os/specs/2026-01-27-1036-pipeline-orchestrator-core/plan.md`
- **Relevance:** Execution contract and dependency gating assumptions used by spec 08
- **Key patterns:** phase lifecycle, staleness behavior, artifact policy
