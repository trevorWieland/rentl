# References for Log/Event Taxonomy & Sink Protocols

## Similar Implementations

### Log entry schema
- **Location:** `packages/rentl-schemas/src/rentl_schemas/logs.py`
- **Relevance:** Defines JSONL log envelope and required fields
- **Key patterns:** Stable fields, `EventName` validation, `LogLevel`

### Progress update schema
- **Location:** `packages/rentl-schemas/src/rentl_schemas/progress.py`
- **Relevance:** Progress events and payload constraints for streaming updates
- **Key patterns:** `ProgressUpdate` validation, payload requirements

### Core orchestrator log/progress emission
- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Current log/progress emission and event names
- **Key patterns:** `_emit_log`, `_emit_progress`, phase invalidation logs

### Orchestrator ports and event helpers
- **Location:** `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- **Relevance:** Run/phase event names and log builder helpers
- **Key patterns:** `RunEvent`, `build_phase_log`, `build_phase_event_name`

### Ingest/export event helpers
- **Location:** `packages/rentl-core/src/rentl_core/ports/ingest.py`
- **Location:** `packages/rentl-core/src/rentl_core/ports/export.py`
- **Relevance:** Phase-specific event enums and structured log payloads
- **Key patterns:** `*_Event` enums, event-specific payload keys

### Log store protocols and filesystem adapter
- **Location:** `packages/rentl-core/src/rentl_core/ports/storage.py`
- **Location:** `packages/rentl-io/src/rentl_io/storage/filesystem.py`
- **Relevance:** JSONL log storage and adapter patterns
- **Key patterns:** Protocol-defined interfaces, JSONL append semantics

### Log sink adapter
- **Location:** `packages/rentl-io/src/rentl_io/storage/log_sink.py`
- **Relevance:** Sink adapter pattern for log emission
- **Key patterns:** Thin adapter over `LogStoreProtocol`

### Prior specs for context
- **Location:** `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/plan.md`
- **Location:** `agent-os/specs/2026-01-26-1835-run-persistence-artifact-store/plan.md`
- **Location:** `agent-os/specs/2026-01-26-1657-pipeline-orchestrator/plan.md`
- **Relevance:** Defines progress semantics, persistence contracts, and orchestration expectations
