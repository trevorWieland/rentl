# Export Adapter (CSV/JSONL/TXT) — Shaping Notes

## Scope
- Implement export adapters that write translated outputs to CSV/JSONL/TXT
- Strict validation with clear errors; no CLI/config integration in this spec

## Decisions
- Primary input preference: edited lines > translated lines
- Untranslated policy required (error/warn/allow) to prevent raw text leaking by default
- CSV output matches input columns by expanding `metadata.extra` into columns
- JSONL output writes `TranslatedLine` objects, one per line
- TXT output writes translated text per line in order
- Fail fast on schema errors with row/line context

## Context
- Visuals: None
- References: `packages/rentl-core/src/rentl_core/ports/ingest.py`,
  `packages/rentl-io/src/rentl_io/ingest/`,
  `packages/rentl-schemas/src/rentl_schemas/io.py`
- Product alignment: v0.1 playable-patch pipeline (CSV/JSONL/TXT export support)

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
