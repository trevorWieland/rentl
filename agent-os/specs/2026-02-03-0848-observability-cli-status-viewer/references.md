# References for Observability Surface (CLI Status Viewer)

## Similar Implementations

### CLI command structure and responses

- **Location:** `services/rentl-cli/src/rentl_cli/main.py`
- **Relevance:** Defines Typer commands, Rich output, and API response envelope.
- **Key patterns:** CLI as thin adapter, JSON response wrapping, log/progress
  path derivation.

### Orchestrator progress emission

- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Emits progress updates and computes ETA + summaries.
- **Key patterns:** `_emit_phase_progress_update`, progress metric building,
  progress/run summary aggregation.

### Progress schema and helpers

- **Location:** `packages/rentl-schemas/src/rentl_schemas/progress.py`
- **Relevance:** Defines progress metrics, summaries, events, and validation.
- **Key patterns:** Monotonic progress validation, percent/ETA handling.

### Event schemas

- **Location:** `packages/rentl-schemas/src/rentl_schemas/events.py`
- **Relevance:** Defines log event enums and payloads for run/phase events.
- **Key patterns:** Stable event naming and structured data models.

### Progress sink persistence

- **Location:** `packages/rentl-io/src/rentl_io/storage/progress_sink.py`
- **Relevance:** Writes progress JSONL for later status rendering.
- **Key patterns:** JSONL append, file placement under logs/progress.

### Run state snapshot

- **Location:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- **Relevance:** Run state schema used for CLI status snapshots.
- **Key patterns:** Run metadata, phase history, summaries.

### Phase result summaries

- **Location:** `packages/rentl-schemas/src/rentl_schemas/results.py`
- **Relevance:** Defines per-phase completion metrics to show in status viewer.
- **Key patterns:** Phase-specific metric definitions and validation.

### TUI baseline status viewer

- **Location:** `services/rentl-tui/src/rentl_tui/app.py`
- **Relevance:** Minimal read-only status rendering for reference.
- **Key patterns:** Progress display expectations and layout heuristics.
