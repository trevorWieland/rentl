# Signposts

- **Task:** Architecture revision
- **Status:** resolved
- **Problem:** The original benchmark design embedded pipeline execution inside the benchmark command and included a custom MTL baseline generator. This caused an intractable blocker: wiring the real rentl pipeline into the benchmark required full orchestrator infrastructure (storage bundles, run contexts, agent pools) that couldn't be reasonably extracted. The benchmark was also hardcoded to a JP→EN 2-system comparison.
- **Evidence:** `services/rentl-cli/src/rentl_cli/main.py:2393` set `rentl_translations = mtl_translations` as a placeholder. Multiple audit rounds (Task 7 rounds 1-4) failed on this. Agent investigation confirmed orchestrator integration requires `_build_orchestrator`, `_StorageBundle`, `PipelineRunContext`, ingest/export adapters — not feasible as a benchmark subcomponent.
- **Impact:** Benchmark compared MTL against itself (both translations identical). Fundamental architecture was wrong.
- **Solution:** Revised spec.md to make benchmark a pure comparison tool. User runs `rentl run` separately to produce candidate outputs, then `rentl benchmark compare` judges them head-to-head. MTL baseline is just a rentl run with translate-only config. Benchmark is now language-agnostic and supports N-way comparison.
- **Resolution:** user via resolve-blockers 2026-02-10
- **Files affected:** spec.md, plan.md, demo.md (all rewritten)

- **Task:** Task 3
- **Status:** resolved
- **Problem:** `RenpyDialogueParser` defaults `scene_id` to the raw filename stem, but `SourceLine.scene_id`/`line_id` require the `HumanReadableId` pattern (`^[a-z]+(?:_[0-9]+)+$`), so KSRE-style names with hyphens fail validation.
- **Evidence:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py:98` now uses `self.normalize_scene_id(script_path.stem)` and `tests/unit/benchmark/eval_sets/test_parser.py:166` verifies KSRE-style auto-normalization (`scene_id == "scriptasunday_1"`).
- **Impact:** Parser now accepts KSRE-style filenames without manual `scene_id` overrides.
- **Solution:** Implemented via `normalize_scene_id` and regression tests.
- **Resolution:** do-task round 2 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py`, `tests/unit/benchmark/eval_sets/test_parser.py`

- **Task:** Task 3
- **Status:** resolved
- **Problem:** Committed manifest hashes are placeholder empty-file SHA-256 values (`e3b0...`) and do not match real KSRE script contents, so runtime hash validation fails immediately.
- **Evidence:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:6` stores `e3b0...`; `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:92` enforces equality. Repro command output: `expected=e3b0...`, `actual=3b287fc5137494cfaaf8ff370554ac084ee48651b9026e2abd105e64770db446`, `MISMATCH`. End-to-end repro via loader+downloader raises `ValueError: Hash validation failed for script-a1-sunday.rpy`.
- **Impact:** Benchmark eval-set download path is not runnable with committed Task 3 artifacts.
- **Solution:** Downloaded real KSRE scripts and computed their SHA-256 hashes. Updated manifest.json with real hashes.
- **Resolution:** do-task round 3 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py`, `tests/unit/benchmark/eval_sets/test_loader.py`

- **Task:** Task 3
- **Status:** resolved
- **Problem:** The committed `demo` slice does not satisfy the task contract requiring dialogue, narration, choices, and multiple speakers.
- **Evidence:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:8` defines `[1, 30]` for `script-a1-sunday.rpy`. Parsing lines 1-30 of the upstream script with `RenpyDialogueParser` produced `parsed_lines=5`, `narration=5`, `speakers=[]`, `menu_choices=0`.
- **Impact:** The configured demo slice cannot exercise the intended parser/aligner/judge behaviors for mixed content types.
- **Solution:** Updated slices.json to use script-a1-monday.rpy lines 550-649 which contains 26 parseable lines with dialogue, narration, 2 menu choices, and multiple speakers.
- **Resolution:** do-task round 3 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json`, `tests/unit/benchmark/eval_sets/test_loader.py`

- **Task:** Task 5 (pre-revision)
- **Status:** resolved
- **Problem:** BDD integration scenarios did not bind table-based Given steps, and head-to-head coverage missed randomized remapping/per-dimension winners.
- **Evidence:** Audit round 2 passed after fixes. `pytest -q tests/unit/benchmark/test_judge.py tests/integration/benchmark/test_judge_flow.py` passes 23/23.
- **Impact:** None — fixed before architecture revision.
- **Solution:** Fixed step bindings and added randomization/per-dimension coverage.
- **Resolution:** do-task round 6 (2026-02-09)
- **Files affected:** `tests/integration/benchmark/test_judge_flow.py`, `tests/unit/benchmark/test_judge.py`, `packages/rentl-core/src/rentl_core/benchmark/judge.py`
- **Note:** Judge module will be further revised in new Task 5 to remove isolated scoring and reference modes.

- **Task:** Task 2
- **Status:** resolved
- **Problem:** `make check` fails with type errors in judge.py, report.py, and main.py after removing isolated scoring schemas (LineScore, RubricScore, DimensionAggregate, TranslationResult, HeadToHeadSummary).
- **Evidence:** Schema files typecheck cleanly (`uv run pyright packages/rentl-schemas/src/rentl_schemas/benchmark/*.py` → 0 errors). Schema unit tests pass (`pytest tests/unit/benchmark/test_rubric.py tests/unit/benchmark/test_report.py` → 16/16 passed). Full `make check` fails with: `error[unresolved-import]: Module rentl_schemas.benchmark.rubric has no member LineScore` (judge.py:16, report.py:17, main.py:86), `error[unresolved-import]: Module rentl_schemas.benchmark.report has no member DimensionAggregate` (report.py:11), `error[missing-argument]: No arguments provided for required parameters candidate_a_name, candidate_b_name` (judge.py:448).
- **Impact:** Task 2 schema revision is complete and correct. Downstream modules (judge, report generator, CLI) have not been updated yet — they will be fixed in Tasks 4, 5, 6, and 7.
- **Solution:** Completed Task 2 schema changes. The schemas are correct and fully tested. Type errors in OTHER modules are expected and addressed by the task plan's dependency structure (Task 2 → Task 4 → Task 5 → Task 6 → Task 7).
- **Resolution:** do-task round 1 (2026-02-10)
- **Files affected:** `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py`, `packages/rentl-schemas/src/rentl_schemas/benchmark/config.py`, `packages/rentl-schemas/src/rentl_schemas/benchmark/__init__.py`, `tests/unit/benchmark/test_rubric.py`, `tests/unit/benchmark/test_report.py`

- **Task:** Task 4
- **Status:** resolved
- **Problem:** Task 4 round-6 fixes updated benchmark dead code, but `test_cli_command` still targets removed symbols and pre-revision benchmark behavior.
- **Evidence:** `pytest -q tests/integration/benchmark/test_cli_command.py` fails 4 tests. Exact errors include `AttributeError: module 'rentl_cli.main' has no attribute 'RubricJudge'` at `tests/integration/benchmark/test_cli_command.py:183`, and assertion failure at `tests/integration/benchmark/test_cli_command.py:489` because stdout is `This command is currently being rewritten.\nUse will be available after Task 7 completion.\n`. The stub behavior is intentional in `services/rentl-cli/src/rentl_cli/main.py:1113` through `services/rentl-cli/src/rentl_cli/main.py:1115`.
- **Impact:** Task 4 cannot remain checked off because its claimed integration-coverage cleanup still leaves a red benchmark CLI integration suite.
- **Solution:** Removed stale `RubricJudge` monkeypatch. Simplified BDD feature file to single stub-focused scenario. Rewrote test file to match stub behavior (exit code 1 with "being rewritten" message). All integration tests now pass.
- **Resolution:** do-task round 7 (2026-02-10)
- **Files affected:** `tests/integration/benchmark/test_cli_command.py`, `tests/features/benchmark/cli_command.feature`

- **Task:** Task 5
- **Status:** resolved
- **Problem:** Task 5 was marked complete without finishing its required unit-test migration to pairwise-only judging.
- **Evidence:** `tests/unit/benchmark/test_judge.py:63`, `tests/unit/benchmark/test_judge.py:88`, `tests/unit/benchmark/test_judge.py:135`, `tests/unit/benchmark/test_judge.py:163`, `tests/unit/benchmark/test_judge.py:189`, `tests/unit/benchmark/test_judge.py:276`, `tests/unit/benchmark/test_judge.py:314`, and `tests/unit/benchmark/test_judge.py:348` still contain `pytest.mark.skip` tests that target removed isolated-scoring APIs (`_build_reference_based_prompt`, `_build_reference_free_prompt`, `_parse_rubric_scores`, `score_translation`, `score_batch`). Verification run: `pytest -q tests/unit/benchmark/test_judge.py tests/integration/benchmark/test_judge_flow.py` → `13 passed, 8 skipped`.
- **Impact:** Legacy skip placeholders hide unfinished migration work and allow Task 5 to appear complete without actively enforcing pairwise-only behavior in the full unit suite.
- **Solution:** Removed all 8 skipped tests targeting isolated-scoring APIs. Remaining 11 tests cover pairwise comparison exclusively. Verification: `pytest -q tests/unit/benchmark/test_judge.py` → `11 passed`, `make check` → ✅ all gates pass.
- **Resolution:** do-task round 8 (2026-02-10)
- **Files affected:** `tests/unit/benchmark/test_judge.py`
