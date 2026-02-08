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

## Sample Data
- `samples/golden/script.jsonl` — Original license-safe sample script
- `samples/golden/LICENSE` — CC0 license
- `samples/golden/artifacts/` — Golden artifacts for each pipeline phase
- `samples/style-guide.md` — Style guide reference

## Test Infrastructure
- `tests/conftest.py` — Root fixtures
- `tests/unit/conftest.py` — Unit test markers
- `tests/integration/conftest.py` — Integration fixtures (FakeLlmRuntime, cli_runner, etc.)
- `tests/integration/steps/cli_steps.py` — BDD step definitions

## Config
- `rentl.toml` — Project config (input_path now points to samples/golden/script.jsonl)
- `rentl.toml.example` — Config template

## Files Updated in Task 6
- `rentl.toml` — input_path updated to samples/golden/script.jsonl
- `debug_test.py` — test config generation updated
- `scripts/validate_agents.py` — docstring example updated
- `.gitignore` — sample_scenes.jsonl entry removed
