# References: Log Redaction & Safety Audit

## Implementation Files

- `packages/rentl-schemas/src/rentl_schemas/logs.py` — LogEntry schema (redaction targets: `data`, `message`)
- `packages/rentl-schemas/src/rentl_schemas/events.py` — Event payloads (CommandStartedData.args has "(redacted)" label but no enforcement)
- `packages/rentl-schemas/src/rentl_schemas/config.py` — ModelEndpointConfig.api_key_env (env var name field)
- `packages/rentl-io/src/rentl_io/storage/log_sink.py` — Log sink implementations (StorageLogSink, ConsoleLogSink, CompositeLogSink, build_log_sink)
- `packages/rentl-io/src/rentl_io/storage/filesystem.py` — FilesystemArtifactStore.write_artifact_jsonl (artifact persistence)
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py` — LogSinkProtocol
- `packages/rentl-core/src/rentl_core/ports/storage.py` — LogStoreProtocol, ArtifactStoreProtocol
- `services/rentl-cli/src/rentl_cli/main.py` — CLI commands, endpoint resolution, build_log_sink wiring

## New Files

- `packages/rentl-schemas/src/rentl_schemas/redaction.py` — Redaction core (SecretPattern, RedactionConfig, Redactor, build_redactor)
- `tests/unit/schemas/test_redaction.py` — Unit tests for redaction patterns and dict traversal
- `tests/unit/cli/test_check_secrets.py` — Unit tests for config scanner

## Issues

- [#34 s0.1.34 Log Redaction & Safety Audit](https://github.com/trevorWieland/rentl/issues/34)

## Dependency Specs

- [s0.1.06 Log/Event Taxonomy & Sink Protocols](../2026-01-26-2206-log-event-taxonomy-sinks/) — Established JSONL schema and sink protocol
- [s0.1.27 End-to-End Logging & Error Surfacing](../2026-02-02-2115-end-to-end-logging-error-surfacing/) — Full logging coverage, noted "Enforce redaction/no-API-key logging" as future work
