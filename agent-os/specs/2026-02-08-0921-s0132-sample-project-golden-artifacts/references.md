# References: Sample Project + Golden Artifacts

## Issue
- https://github.com/trevorWieland/rentl/issues/32

## Dependencies
- s0.1.03, s0.1.04, s0.1.24, s0.1.29 (all completed)

## Schema Models (rentl-schemas)
- `packages/rentl-schemas/src/rentl_schemas/io.py` — SourceLine, TranslatedLine
- `packages/rentl-schemas/src/rentl_schemas/phases.py` — SceneSummary, IdiomAnnotationList, TranslationResultList, StyleGuideReviewList, LineEdit
- `packages/rentl-schemas/src/rentl_schemas/qa.py` — QaIssue, QaSummary, ReviewerNote
- `packages/rentl-schemas/src/rentl_schemas/primitives.py` — LineId, SceneId, RouteId patterns

## Ingest Adapters
- `packages/rentl-io/src/rentl_io/ingest/jsonl_adapter.py` — JSONL ingest adapter

## Existing Sample Data (to be replaced)
- `sample_scenes.jsonl` — Current copyrighted sample (473 lines)
- `samples/style-guide.md` — Style guide reference

## Test Infrastructure
- `tests/conftest.py` — Root fixtures
- `tests/unit/conftest.py` — Unit test markers
- `tests/integration/conftest.py` — Integration fixtures (FakeLlmRuntime, cli_runner, etc.)
- `tests/integration/steps/cli_steps.py` — BDD step definitions

## Config
- `rentl.toml` — Project config (references sample_scenes.jsonl on line 7)
- `rentl.toml.example` — Config template

## Files Referencing sample_scenes.jsonl
- `rentl.toml` — input_path
- `debug_test.py` — test config generation
- `scripts/validate_agents.py` — docstring example
- `.gitignore` — ignore rule
- `agent-os/specs/2026-02-07-0258-s0129-project-bootstrap-command/references.md`
- `agent-os/specs/2026-02-01-1630-initial-phase-agent-translate/plan.md`
- `agent-os/specs/2026-02-03-0848-observability-cli-status-viewer/plan.md`
