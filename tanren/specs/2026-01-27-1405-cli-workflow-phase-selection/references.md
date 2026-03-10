# References for CLI Workflow & Phase Selection

## Similar Implementations

### rentl CLI entry point
- **Location:** `services/rentl-cli/src/rentl_cli/main.py`
- **Relevance:** Current Typer CLI patterns, JSON envelope output, error handling.
- **Key patterns:** `ApiResponse` envelopes, sync-to-async bridging via `asyncio.run`.

### CLI unit tests
- **Location:** `tests/unit/cli/test_main.py`
- **Relevance:** CLI testing style and Typer runner usage.
- **Key patterns:** JSON output assertions, filesystem temp paths.

### Orchestrator core
- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Run/phase execution, progress emission, run state persistence hooks.
- **Key patterns:** `run_plan`, `run_phase`, `_persist_run_state`, `hydrate_run_context`.

### Orchestrator ports
- **Location:** `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- **Relevance:** Log/progress sink protocols and structured orchestration errors.
- **Key patterns:** `LogSinkProtocol`, `ProgressSinkProtocol`, `OrchestrationErrorInfo`.

### Storage ports
- **Location:** `packages/rentl-core/src/rentl_core/ports/storage.py`
- **Relevance:** Storage protocol interfaces and error shapes for CLI surfacing.
- **Key patterns:** `RunStateStoreProtocol`, `ArtifactStoreProtocol`, `LogStoreProtocol`.

### Filesystem storage adapters
- **Location:** `packages/rentl-io/src/rentl_io/storage/filesystem.py`
- **Relevance:** Default storage implementation used by CLI for run state, artifacts, and logs.
- **Key patterns:** run index paths, artifact JSONL writing, log storage.

### Log sink adapter
- **Location:** `packages/rentl-io/src/rentl_io/storage/log_sink.py`
- **Relevance:** Bridge between log sink protocol and log store.
- **Key patterns:** `StorageLogSink`, `CompositeLogSink`.

### Progress sink adapters
- **Location:** `packages/rentl-io/src/rentl_io/storage/progress_sink.py`
- **Relevance:** JSONL progress stream handling for CLI observability.
- **Key patterns:** `FileSystemProgressSink`, `CompositeProgressSink`.

### Ingest/export routers
- **Location:** `packages/rentl-io/src/rentl_io/ingest/router.py`
- **Relevance:** Adapter selection by format to keep CLI thin.
- **Key patterns:** `get_ingest_adapter`, `load_source`.

- **Location:** `packages/rentl-io/src/rentl_io/export/router.py`
- **Relevance:** Export adapter routing and selection of phase outputs.
- **Key patterns:** `write_output`, `select_export_lines`, `write_phase_output`.

### Config schemas and validation
- **Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`
- **Relevance:** Source of truth for run config shape and validation rules.
- **Key patterns:** `RunConfig`, `PipelineConfig`, `PhaseExecutionConfig`.

- **Location:** `packages/rentl-schemas/src/rentl_schemas/validation.py`
- **Relevance:** Config validation entrypoints for CLI use.
- **Key patterns:** `validate_run_config`.

### Storage + response schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/storage.py`
- **Relevance:** Run state and artifact schemas used in CLI responses.
- **Key patterns:** `RunStateRecord`, `LogFileReference`, `ArtifactMetadata`.

- **Location:** `packages/rentl-schemas/src/rentl_schemas/responses.py`
- **Relevance:** Response envelope used by CLI output.
- **Key patterns:** `ApiResponse`, `ErrorResponse`, `MetaInfo`.
