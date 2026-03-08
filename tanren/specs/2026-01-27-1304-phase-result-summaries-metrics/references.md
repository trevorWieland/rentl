# References for Phase Result Summaries & Metrics

## Similar Implementations

### Pipeline Orchestrator
- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Phase execution, progress emission, phase history, and log payloads.
- **Key patterns:** `_build_phase_log_data`, `_build_phase_record`, progress summaries.

### Orchestrator Ports
- **Location:** `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- **Relevance:** Phase/run log helpers and event conventions.
- **Key patterns:** `build_phase_log`, event suffixes, JSONL data payloads.

### Storage Ports
- **Location:** `packages/rentl-core/src/rentl_core/ports/storage.py`
- **Relevance:** Run state persistence and structured errors.
- **Key patterns:** `RunStateStoreProtocol`, durable run snapshots.

### Pipeline Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- **Relevance:** Phase history records and run state snapshot schema.
- **Key patterns:** `PhaseRunRecord`, `RunState`.

### Progress Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/progress.py`
- **Relevance:** Metric allowlists and validation logic.
- **Key patterns:** `PHASE_METRIC_DEFINITIONS`, `ProgressMetric` validators.

### Phase Output Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Relevance:** Outputs used to compute summaries (glossary, annotations, edits).
- **Key patterns:** `ContextPhaseOutput`, `PretranslationPhaseOutput`, `EditPhaseOutput`.

### QA Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/qa.py`
- **Relevance:** Issue summaries by category and severity.
- **Key patterns:** `QaSummary`, `QaIssue`.

### Events Taxonomy
- **Location:** `packages/rentl-schemas/src/rentl_schemas/events.py`
- **Relevance:** Phase completion events for log payloads.
- **Key patterns:** `PhaseEventSuffix`, `ProgressEvent`.

### Export Summary
- **Location:** `packages/rentl-core/src/rentl_core/ports/export.py`
- **Relevance:** Export result fields for phase metrics.
- **Key patterns:** `ExportSummary`, `ExportResult`.
