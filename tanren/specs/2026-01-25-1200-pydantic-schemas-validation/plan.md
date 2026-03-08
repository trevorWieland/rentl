# Pydantic Schemas and Validation Plan

## Goal
- Ship the initial Pydantic schemas and validation for the v0.1 pipeline
- Keep schemas strict and extensible for v0.2 multi-agent teams and richer QA
- Centralize shared schemas in `rentl-schemas`

## Execution Note
- Execute Task 1 now, then pause before implementation

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals

## Task 2: Define schema inventory and package layout
- Use `packages/rentl-schemas/src/rentl_schemas/` as the shared schema home
- Map modules for config, pipeline state, phases, IO, QA, logs, responses, and primitives
- Define schema versioning and ownership boundaries across packages

## Task 3: Build core primitives and base models
- Create a BaseSchema with strict Pydantic config (extra=forbid)
- Define typed primitives: RunId, PhaseName, LanguageCode, FileFormat, Timestamp, JsonValue
- Enforce Field descriptions and built-in validators on every field

## Task 4: Config schemas (TOML-backed)
- Project and language config, BYOK model settings, concurrency, rate limits, cache
- Pipeline and phase config (enabled phases, ordering, phase parameters)
- Validation rules for required combinations and mutually exclusive settings

## Task 5: Pipeline run state and artifacts
- Run metadata (ids, status, timestamps, current phase), error details, progress counters
- Artifact references for inputs, outputs, JSONL logs, QA reports
- QA and translation summary stats for v0.1

## Task 6: Phase input and output schemas with v0.2 extensions
- Define v0.1 IO models for context, pretranslation, translate, QA, and edit
- Add richer QA categories and define extension points for future multi-agent work

## Task 7: Cross-cutting response and log schemas
- Implement API response envelope {data, error, meta} per standard
- Implement JSONL log entry schema with typed data using JsonValue

## Task 8: Validation helpers and tests
- Add validation entrypoints in `rentl_schemas` for config and phase IO
- Add unit tests in `tests/unit/schemas/` for validators and serialization rules
- Ensure strict typing (no Any) and Field descriptions everywhere
