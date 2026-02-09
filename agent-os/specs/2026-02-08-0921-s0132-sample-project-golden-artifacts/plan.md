spec_id: s0.1.32
issue: https://github.com/trevorWieland/rentl/issues/32
version: v0.1

# Plan: Sample Project + Golden Artifacts

## Decision Record

rentl needs a bundled, license-safe sample project for three purposes: (1) smoke/integration testing with validated golden artifacts, (2) product demo for new users to see what the pipeline produces, and (3) a default input for `rentl run` out of the box. The existing `sample_scenes.jsonl` is copyrighted and must be replaced.

We're writing an original Japanese VN script rather than sourcing one externally because freely-licensed game scripts of the right size and variety are extremely scarce, and original content gives us full control over what pipeline features we exercise.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on issue branch

- [x] Task 2: Write the Sample Script
  - Create `samples/golden/script.jsonl` with an original Japanese VN-style script
  - At least 3 scenes, 2+ routes, 4+ named speakers
  - Include dialogue lines, narration lines, and at least one choice (`is_choice: true`)
  - Include lines with `"???"` speaker for future speaker-identification testing
  - Include culturally-specific expressions: idioms, honorifics, onomatopoeia
  - Target 50–80 lines — small but representative
  - All line_ids follow `^[a-z]+(?:_[0-9]+)+$` pattern (e.g. `scene_001_0001`)
  - Add `samples/golden/LICENSE` with CC0 text
  - Acceptance: file parses as valid JSONL, every line validates as SourceLine

- [x] Task 3: Generate Golden Artifacts
  - Create `samples/golden/artifacts/` directory
  - `context.jsonl` — SceneSummary for each scene (scene_id, summary, characters list)
  - `pretranslation.jsonl` — IdiomAnnotationList with idiom annotations for culturally-specific lines
  - `translate.jsonl` — TranslationResultList with English translations for every line
  - `qa.jsonl` — StyleGuideReviewList with sample violations (at least one per QA category)
  - `edit.jsonl` — LineEdit records showing corrections applied from QA findings
  - `export.jsonl` — Final TranslatedLine records (complete translated output)
  - All artifacts must validate against rentl-schemas Pydantic models
  - Acceptance: zero validation errors for every artifact file
  - [x] Fix: Satisfy QA coverage requirement by representing all QA categories (`grammar`, `terminology`, `style`, `consistency`, `formatting`, `context`, `cultural`, `other`) instead of only 4 rule labels in `samples/golden/artifacts/qa.jsonl` (see `packages/rentl-schemas/src/rentl_schemas/primitives.py:155` and `samples/golden/artifacts/qa.jsonl:1`) (audit round 1)
  - [x] Fix: Clarify and enforce category mapping in artifact generation/tests so Task 3's "at least one per QA category" is machine-checkable (current output only exposes `rule_violated` free text) (`agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:35`, `packages/rentl-schemas/src/rentl_schemas/phases.py:89`) (audit round 1)
  - [x] Fix: Add at least one explicit `Other: ...` violation in `samples/golden/artifacts/qa.jsonl` so all 8 `QaCategory` enum values are represented (`packages/rentl-schemas/src/rentl_schemas/primitives.py:155`, `samples/golden/artifacts/qa.jsonl:1`) (audit round 2)
  - [x] Fix: Make category coverage machine-checkable by converting remaining non-prefixed `rule_violated` values (`Onomatopoeia formatting`, `Onomatopoeia consistency`) to the `<Category>: <specific rule>` format used in `samples/golden/artifacts/README.md:22` (`samples/golden/artifacts/qa.jsonl:1`) (audit round 2)

- [x] Task 4: Schema Validation Tests (Unit Tier)
  - Add `tests/unit/test_golden_artifacts.py`
  - Test loads each golden artifact file and validates against its Pydantic model
  - Test verifies script.jsonl lines validate as SourceLine
  - Each test <250ms
  - Follow existing unit test patterns (pytest.mark.unit auto-applied)
  - Acceptance: `make check` passes, all golden artifact tests green

- [x] Task 5: Ingest Integration Test
  - Add BDD-style integration test in `tests/integration/`
  - Given: the golden script.jsonl file
  - When: ingested through the JSONL adapter
  - Then: output SourceLine records match golden data (line_ids, text, speakers, scenes)
  - Use existing integration test fixtures and patterns
  - Acceptance: test passes, <5s
  - [x] Fix: Replace sampled assertions with full-record equality checks for all ingested lines (`line_id`, `text`, `speaker`, `scene_id`) against `samples/golden/script.jsonl`; current checks only validate subsets/patterns (`tests/integration/ingest/test_golden_script.py:72`, `tests/integration/ingest/test_golden_script.py:98`, `tests/integration/ingest/test_golden_script.py:114`, `tests/integration/ingest/test_golden_script.py:138`) (audit round 1)

- [x] Task 6: Replace sample_scenes.jsonl
  - Update `rentl.toml` input_path → `samples/golden/script.jsonl`
  - Update `scripts/validate_agents.py` docstring reference
  - Update `debug_test.py` input_path reference
  - Update `.gitignore` — remove `sample_scenes.jsonl` entry, add `samples/golden/` exclusions if needed
  - Delete `sample_scenes.jsonl` from repo
  - Update relevant spec doc references
  - Acceptance: no broken operational references, `git grep sample_scenes.jsonl -- ':(exclude)agent-os/specs/'` returns zero results (spec docs may retain historical mentions)
  - [x] Fix: Make Task 6 acceptance machine-checkable for operational references by scoping the grep command (or equivalent verification) so intentional historical mentions in spec docs do not fail the task; current `git grep sample_scenes.jsonl` still returns matches at `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/demo.md:17`, `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:9`, `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:69`, and `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/spec.md:9` (audit round 1)

- [x] Task 7: Full Pipeline Smoke Test
  - Add quality test that runs the full pipeline on the sample script
  - Uses real LLM runtime (no mocking, requires HTTP endpoint)
  - Assert all phases (ingest → context → pretranslation → translate → QA → edit → export) complete
  - Assert export output is valid TranslatedLine data
  - BDD-style with Given/When/Then
  - Acceptance: test passes, <30s, `make all` green
  - NOTE: Test requires RENTL_QUALITY_API_KEY and RENTL_QUALITY_BASE_URL environment variables; skips gracefully if not configured
  - [x] Fix: Move test from integration to quality layer to resolve FakeLlmRuntime incompatibility with agent pool execution (agents make direct HTTP calls via pydantic-ai that bypass CLI runtime injection); quality tests use real HTTP endpoints per layer rules (audit round 1) (See the human feedback in the relevant signpost, this is FULLY intentional, and is not something that should be ignored.)
  - [x] Fix: Make the Task 7 smoke test self-contained by setting required endpoint auth env vars in test setup; current config uses `api_key_env = "PRIMARY_KEY"` at `tests/quality/pipeline/test_golden_script_pipeline.py:68` but no setup sets it, causing `config_error: Missing API key environment variable: PRIMARY_KEY` at assertion point `tests/quality/pipeline/test_golden_script_pipeline.py:192` (audit round 2)
  - [x] Fix: Strengthen the "all phases complete" assertion to verify per-phase execution (not just exit code/run_id); current checks in `tests/quality/pipeline/test_golden_script_pipeline.py:177` only assert success envelope and do not confirm each configured phase ran (audit round 2)
  - [x] Fix: Use RENTL_QUALITY_API_KEY and RENTL_QUALITY_BASE_URL environment variables (matching other quality tests) and add pytest.mark.skipif to skip test when environment is not configured; removed mock server approach which was incompatible with quality test requirements for real endpoints (audit round 4)

- [x] Fix: Remove hardcoded golden script line-count assertion (`58`) in ingest integration test so new scenes/lines can be added without breaking tests, while retaining full-record equality checks against the file contents (`tests/integration/ingest/test_golden_script.py:64`, `tests/integration/ingest/test_golden_script.py:65`, `tests/integration/ingest/test_golden_script.py:66`; spec non-negotiable extensibility requirement at `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/spec.md:46`) (spec audit round 1)
