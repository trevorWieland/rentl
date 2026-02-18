---
standard: log-line-format
category: architecture
score: 100
importance: High
violations_count: 0
date: 2026-02-18
status: clean
---

# Standards Audit: Log Line Format

**Standard:** `architecture/log-line-format`
**Date:** 2026-02-18
**Score:** 100/100
**Importance:** High

## Summary

Log-line emission is consistently routed through `LogEntry` models and dedicated builders before persistence. All observed production log producers (pipeline lifecycle, ingest/export/phase/artifact events, agent telemetry, and CLI command logs) emit schema-conforming fields with snake_case event names and explicit levels. Storage and sink implementations write one `model_dump_json` string per line in UTF-8 files/streams, so current adherence appears complete.

## Violations

No violations found.

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/logs.py:18` — `LogEntry` defines the required field set (`timestamp`, `level`, `event`, `run_id`, `phase`, `message`, `data`) with constrained types.
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py:185` — run-level logs are built via `build_run_started_log` as a typed `LogEntry` with required fields and enum event values.
- `packages/rentl-core/src/rentl_core/ports/ingest.py:138` and `packages/rentl-core/src/rentl_core/ports/export.py:166` — ingest/export log constructors follow the same schema and use snake_case event enums (`ingest_*`, `export_*`).
- `packages/rentl-io/src/rentl_io/storage/log_sink.py:58` and `packages/rentl-io/src/rentl_io/storage/filesystem.py:546` — both sinks serialize entries with `model_dump_json` and append newline-delimited JSON to UTF-8 output.
- `services/rentl-cli/src/rentl/main.py:1931` — CLI command logs (`command_started`, `command_completed`, `command_failed`) are emitted as `LogEntry` through standardized builders.

## Scoring Rationale

- **Coverage:** 100% of relevant production log producers and sinks reviewed use the stable `LogEntry` schema.
- **Severity:** No critical/high/medium issues found.
- **Trend:** Both older core orchestration paths and newer CLI/logging utilities share the same schema-first approach.
- **Risk:** Low: no practical risk identified from fragmented or non-JSONL log formats.
