# Signposts

- **Task:** Task 3 (Generate Golden Artifacts)
- **Problem:** Task 3 requires `qa.jsonl` to include sample violations "at least one per QA category", but the produced artifact stores only free-text `rule_violated` labels and currently covers only four labels.
- **Evidence:** `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:35`; `packages/rentl-schemas/src/rentl_schemas/primitives.py:155` defines 8 QA categories (`grammar`, `terminology`, `style`, `consistency`, `formatting`, `context`, `cultural`, `other`); `samples/golden/artifacts/qa.jsonl:1`..`samples/golden/artifacts/qa.jsonl:4` contains only `Onomatopoeia formatting`, `Onomatopoeia consistency`, `Sentence completeness`, `Honorific consistency`.
- **Impact:** Future tasks/tests that expect category-level QA coverage cannot verify completeness from current golden QA data; this blocks deterministic checks tied to category coverage.

- **Task:** Task 3 (Generate Golden Artifacts)
- **Problem:** The follow-up Task 3 fix still misses `other` coverage and leaves non-prefixed `rule_violated` entries, so category coverage cannot be strictly derived from a single convention.
- **Evidence:** `packages/rentl-schemas/src/rentl_schemas/primitives.py:155` includes `OTHER`; `samples/golden/artifacts/qa.jsonl:1` uses `Onomatopoeia formatting` and `Onomatopoeia consistency` (no `<Category>:` prefix), and `samples/golden/artifacts/qa.jsonl:1`..`samples/golden/artifacts/qa.jsonl:4` contain no `Other:` violation; `samples/golden/artifacts/README.md:22` defines the required `<Category>: <specific rule>` convention.
- **Impact:** Any deterministic check for "all QA categories represented" remains brittle and can silently pass/fail depending on ad-hoc inference rules rather than explicit category labels.

- **Task:** Task 5 (Ingest Integration Test)
- **Problem:** The ingest BDD test uses spot checks and pattern checks instead of verifying full record equality with the golden script, so regressions in later rows can pass undetected.
- **Evidence:** Plan contract requires matching golden data for `line_ids`, `text`, `speakers`, and `scenes` (`agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:57`), but assertions only sample the first IDs (`tests/integration/ingest/test_golden_script.py:77`), first text line (`tests/integration/ingest/test_golden_script.py:103`), selected speakers (`tests/integration/ingest/test_golden_script.py:119`), and scene-count heuristics (`tests/integration/ingest/test_golden_script.py:143`).
- **Impact:** Adapter regressions that alter ordering or values outside sampled rows can still pass Task 5, weakening confidence in ingest correctness before Task 7 pipeline smoke coverage.
