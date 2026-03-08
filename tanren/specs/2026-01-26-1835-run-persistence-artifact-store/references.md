# References for Run Persistence & Artifact Store Protocols

## Similar Implementations

### Pipeline run schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- **Relevance:** Defines run state, artifact references, and phase history
- **Key patterns:** Run metadata, artifact references, history/staleness markers

### JSONL log schema
- **Location:** `packages/rentl-schemas/src/rentl_schemas/logs.py`
- **Relevance:** JSONL log entry format used by log sinks
- **Key patterns:** Stable `{timestamp, level, event, run_id, phase, message, data}` schema

### Orchestrator ports
- **Location:** `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- **Relevance:** Log/progress sink protocols and run lifecycle events
- **Key patterns:** Async protocols, event naming, structured errors

### JSONL writer adapter
- **Location:** `packages/rentl-io/src/rentl_io/export/jsonl_adapter.py`
- **Relevance:** Example of JSONL output writing with async wrappers
- **Key patterns:** `asyncio.to_thread` file IO, validation, structured errors
