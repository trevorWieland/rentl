# References for Pipeline Orchestrator

## Similar Implementations

### Progress semantics
- **Location:** `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/`
- **Relevance:** Defines progress schemas and monotonic invariants used by orchestration updates.
- **Key patterns:** `RunProgress`, `PhaseProgress`, `ProgressUpdate` lifecycle events.

### Import/export adapters
- **Location:** `agent-os/specs/2026-01-26-1223-import-adapter/`, `agent-os/specs/2026-01-26-1449-export-adapter/`
- **Relevance:** Defines adapter protocols and log event builders for ingest/export phases.
- **Key patterns:** Port protocols in `rentl-core`, error schemas, log helper patterns.

### Phase schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Relevance:** Canonical inputs/outputs for context, pretranslation, translate, QA, edit.
- **Key patterns:** Strict Pydantic models with descriptions and validators.

### Pipeline and progress state
- **Location:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`, `packages/rentl-schemas/src/rentl_schemas/progress.py`
- **Relevance:** Run metadata, artifacts, and progress tracking primitives.
- **Key patterns:** `RunState`, `RunProgress`, metrics/summary computation.

### Config and ordering
- **Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`
- **Relevance:** Pipeline phase ordering and per-phase configuration structure.
- **Key patterns:** Canonical phase order, validation rules.

### Log schema
- **Location:** `packages/rentl-schemas/src/rentl_schemas/logs.py`
- **Relevance:** JSONL log entry shape used for orchestration events.
- **Key patterns:** Stable `{timestamp, level, event, run_id, phase, message, data}` envelope.
