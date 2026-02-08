# Signposts

- **Task:** Task 3 (Generate Golden Artifacts)
- **Problem:** Task 3 requires `qa.jsonl` to include sample violations "at least one per QA category", but the produced artifact stores only free-text `rule_violated` labels and currently covers only four labels.
- **Evidence:** `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:35`; `packages/rentl-schemas/src/rentl_schemas/primitives.py:155` defines 8 QA categories (`grammar`, `terminology`, `style`, `consistency`, `formatting`, `context`, `cultural`, `other`); `samples/golden/artifacts/qa.jsonl:1`..`samples/golden/artifacts/qa.jsonl:4` contains only `Onomatopoeia formatting`, `Onomatopoeia consistency`, `Sentence completeness`, `Honorific consistency`.
- **Impact:** Future tasks/tests that expect category-level QA coverage cannot verify completeness from current golden QA data; this blocks deterministic checks tied to category coverage.
