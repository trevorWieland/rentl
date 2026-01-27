# Import Adapter (CSV/JSONL/TXT) Plan

## Goal
- Provide the v0.1 import adapter to parse CSV/JSONL/TXT into `SourceLine` records
- Enforce strict schema validation and clear error reporting
- Keep the adapter async-first and isolated from CLI wiring

## Execution Note
- Execute Task 1 now, then continue with implementation tasks

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals

## Task 2: Define ingest protocol + errors in core
- Add a core domain protocol (async) for ingest adapters that returns `list[SourceLine]`
- Define typed ingest error models (code/message/details with row or line context)
- Export protocol + errors via `packages/rentl-core/src/rentl_core/__init__.py`

## Task 3: Define format mapping + validation rules
- CSV: required columns `line_id`, `text`; optional `scene_id`, `speaker`, `metadata`
- JSONL: each line is a JSON object compatible with `SourceLine`
- TXT: one line per record, auto-generate `line_id` values (`line_1`, `line_2`, ...)
- Extra CSV columns fold into `metadata` (merged with parsed `metadata` JSON if provided)
- Fail fast on validation errors with row/line numbers in error details

## Task 4: Implement adapters in rentl-io
- Create `packages/rentl-io/src/rentl_io/ingest/` with CSV/JSONL/TXT adapters
- Add a format router that selects an adapter based on `IngestSource.format`
- Use `asyncio.to_thread` for file IO and construct `SourceLine` for validation

## Task 5: Logging + response integration touchpoints
- Document ingest event names aligned to JSONL log schema
- Map ingest errors to API response envelope for future CLI/TUI use

## Task 6: Tests (unit)
- CSV/JSONL/TXT happy paths and validation failures
- Invalid `line_id`/`scene_id` patterns
- Missing required fields
- Metadata parsing and extra column merging
- TXT line index metadata

## References Studied
- `packages/rentl-schemas/src/rentl_schemas/io.py`
- `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- `packages/rentl-schemas/src/rentl_schemas/phases.py`

## Standards Applied
- architecture/adapter-interface-protocol
- architecture/thin-adapter-pattern
- architecture/naming-conventions
- architecture/log-line-format
- architecture/api-response-format
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- architecture/none-vs-empty

## Product Alignment
- v0.1 scope: CSV/JSONL/TXT import for the playable-patch pipeline
