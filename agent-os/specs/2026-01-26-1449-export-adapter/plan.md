# Export Adapter (CSV/JSONL/TXT) Plan

## Goal
- Provide the v0.1 export adapter to write translated outputs to CSV/JSONL/TXT
- Enforce strict schema validation, deterministic output ordering, and clear error reporting
- Keep the adapter async-first and isolated from CLI wiring

## Execution Note
- Execute Task 1 now, then continue with implementation tasks

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals

## Task 2: Define export protocol + errors in core
- Add a core domain protocol (async) for export adapters that writes translated output
- Define typed export error models (code/message/details with row or line context)
- Add export event log helpers aligned to JSONL log schema
- Export protocol + errors via `packages/rentl-core/src/rentl_core/__init__.py`

## Task 3: Define format mapping + untranslated policy
- Primary input preference: EditPhaseOutput.edited_lines, fallback to TranslatePhaseOutput.translated_lines
- CSV: match input columns by expanding `metadata.extra` into columns; include `metadata` JSON for remaining keys
- JSONL: one `TranslatedLine` JSON per line
- TXT: one translated text per line in order
- Define untranslated policy (error/warn/allow) and enforce for export
- Fail fast on validation errors with row/line numbers in error details

## Task 4: Implement adapters in rentl-io
- Create `packages/rentl-io/src/rentl_io/export/` with CSV/JSONL/TXT adapters
- Add a format router that selects an adapter based on `ExportTarget.format`
- Use `asyncio.to_thread` for file IO and construct `TranslatedLine` for validation

## Task 5: Router + response integration touchpoints
- Expose export router and adapter classes via `rentl-io` package exports
- Map export errors to API response envelope for future CLI/TUI use

## Task 6: Tests (unit)
- CSV/JSONL/TXT happy paths and validation failures
- Untranslated policy behaviors (error vs allow)
- Metadata expansion into CSV columns and metadata JSON preservation
- Output ordering and required fields

## Task 7: Make All Gate
- Run `make all`
- Fix failures and re-run until green

## References Studied
- `packages/rentl-core/src/rentl_core/ports/ingest.py`
- `packages/rentl-io/src/rentl_io/ingest/`
- `packages/rentl-schemas/src/rentl_schemas/io.py`
- `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- `packages/rentl-schemas/src/rentl_schemas/phases.py`

## Standards Applied
- architecture/adapter-interface-protocol
- architecture/thin-adapter-pattern
- architecture/naming-conventions
- architecture/log-line-format
- architecture/api-response-format
- architecture/none-vs-empty
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- testing/make-all-gate

## Product Alignment
- v0.1 scope: CSV/JSONL/TXT export for the playable-patch pipeline
