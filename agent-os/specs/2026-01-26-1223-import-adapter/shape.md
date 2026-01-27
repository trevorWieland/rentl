# Import Adapter (CSV/JSONL/TXT) — Shaping Notes

## Scope
- Implement import adapters that parse CSV/JSONL/TXT into `SourceLine`
- Strict validation with clear errors; no CLI/config wiring in this spec

## Decisions
- Parsing + normalization only; CLI/config integration is out of scope
- Output model is `SourceLine` from `rentl-schemas`
- CSV/JSONL require `line_id` and `text`; `scene_id`, `speaker`, `metadata` optional
- TXT auto-generates `line_id` as `line_1`, `line_2`, ...
- Extra CSV columns fold into `metadata` (merge with parsed `metadata` JSON)
- Fail fast on schema errors with row/line context

## Context
- Visuals: None
- References: `packages/rentl-schemas/src/rentl_schemas/io.py`
- Product alignment: v0.1 playable-patch pipeline (CSV/JSONL/TXT support)

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
