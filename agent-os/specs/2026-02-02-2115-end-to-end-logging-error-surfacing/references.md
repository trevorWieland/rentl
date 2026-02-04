# References for End-to-End Logging & Error Surfacing

## Similar Implementations

### Pipeline orchestrator logging + progress

- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Existing run/phase logging, progress events, and error surfacing.
- **Key patterns:** `build_phase_log`, `build_run_failed_log`, progress update emission.

### Log schema + event taxonomy

- **Location:** `packages/rentl-schemas/src/rentl_schemas/logs.py`
- **Relevance:** Canonical JSONL schema for log entries.
- **Key patterns:** `LogEntry` schema and typed primitives.

### Event taxonomy

- **Location:** `packages/rentl-schemas/src/rentl_schemas/events.py`
- **Relevance:** Standard run/phase/ingest/export events.
- **Key patterns:** `RunEvent`, `PhaseEventSuffix`, `IngestEvent`, `ExportEvent`.

### Log sink adapters

- **Location:** `packages/rentl-io/src/rentl_io/storage/log_sink.py`
- **Relevance:** Storage-backed and composite log sink adapters.
- **Key patterns:** `StorageLogSink`, `CompositeLogSink`.

### File-based log store

- **Location:** `packages/rentl-io/src/rentl_io/storage/filesystem.py`
- **Relevance:** JSONL append semantics and error handling.
- **Key patterns:** `FileSystemLogStore.append_log/append_logs`.

### CLI response envelope + errors

- **Location:** `services/rentl-cli/src/rentl_cli/main.py`
- **Relevance:** Error response mapping for CLI JSON output.
- **Key patterns:** `_error_from_exception`, `{data, error, meta}` response usage.

### Structured errors for core ports

- **Location:** `packages/rentl-core/src/rentl_core/ports/ingest.py`
- **Relevance:** Structured error codes and log builders for ingest.
- **Key patterns:** `IngestErrorInfo`, `build_ingest_*_log`.

### Structured errors for core ports

- **Location:** `packages/rentl-core/src/rentl_core/ports/export.py`
- **Relevance:** Structured error codes and log builders for export.
- **Key patterns:** `ExportErrorInfo`, `build_export_*_log`.

### Exception surface areas to centralize

- **Location:**
  - `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
  - `packages/rentl-core/src/rentl_core/ports/storage.py`
  - `packages/rentl-agents/src/rentl_agents/*`
  - `services/rentl-cli/src/rentl_cli/main.py`
- **Relevance:** Scattered exception classes and error handling.
- **Key patterns:** `OrchestrationError`, `StorageError`, agent-specific exceptions.
