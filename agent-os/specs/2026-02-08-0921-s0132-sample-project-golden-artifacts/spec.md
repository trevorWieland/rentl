spec_id: s0.1.32
issue: https://github.com/trevorWieland/rentl/issues/32
version: v0.1

# Spec: Sample Project + Golden Artifacts

## Problem

rentl has no bundled, license-safe sample data. The existing `sample_scenes.jsonl` is from a copyrighted visual novel and cannot be freely redistributed. There are no pre-validated golden artifacts for smoke tests, and new users have no way to see what the pipeline produces without configuring their own project first.

## Goals

- Ship an original, freely-licensed Japanese VN script that exercises every pipeline phase
- Provide golden artifacts (one per phase) validated against rentl-schemas
- Enable schema-validation unit tests and ingest integration tests against the sample data
- Replace `sample_scenes.jsonl` with the new sample as the default input
- Give new users a working demo project out of the box

## Non-Goals

- Generating golden artifacts via actual LLM calls (they are hand-crafted and schema-validated)
- Supporting multiple sample scripts or languages (one Japanese→English sample is sufficient for v0.1)
- Building a benchmark suite (that's s0.1.37)
- Exhaustive coverage of every edge case — the script should be representative, not comprehensive

## Acceptance Criteria

- [ ] Sample script exists at `samples/golden/script.jsonl` containing an original Japanese VN-style script with at least 3 scenes, 2+ routes, 4+ named speakers, dialogue, narration, at least one choice, unknown/ambiguous speakers, and culturally-specific expressions
- [ ] Golden artifacts exist for each pipeline phase: context (SceneSummary), pretranslation (IdiomAnnotationList), translate (TranslationResultList), QA (StyleGuideReviewList), edit (LineEdit), and export (TranslatedLine)
- [ ] All golden artifacts validate against their corresponding rentl-schemas Pydantic models with zero errors
- [ ] Unit tests load every golden artifact file and assert schema compliance (<250ms)
- [ ] Integration test ingests the sample script through the JSONL adapter and asserts output matches golden SourceLine data
- [ ] License file (CC0 or equivalent) is included at `samples/golden/LICENSE`
- [ ] `sample_scenes.jsonl` is removed and all references updated to point to the new sample
- [ ] Full pipeline smoke test runs all phases on the sample script and completes successfully (quality-layer test with real LLM runtime; skips gracefully if endpoint not configured)
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Original content only** — The sample script must be original work, not copied from any existing game. It must be freely redistributable with the license explicitly stated in `samples/golden/LICENSE`.
2. **Schema-valid golden artifacts** — Every golden artifact file must parse and validate against the corresponding rentl Pydantic schema (SourceLine, SceneSummary, TranslationResultList, etc.) with zero validation errors.
3. **Pipeline-exercising variety** — The sample script must include dialogue (multiple speakers), narration, at least one choice, unknown/ambiguous speakers (`"???"`), and culturally-specific content that exercises every pipeline phase (ingest through export).
4. **Extensible structure** — The sample script and golden artifacts must be structured so new lines/scenes can be added without breaking existing golden data or tests.
5. **No test deletions or modifications to make things pass** — Existing tests must continue to pass unmodified.
