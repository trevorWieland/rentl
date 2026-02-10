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
