# Signposts

- **Task:** Task 3
- **Status:** resolved
- **Problem:** `RenpyDialogueParser` defaults `scene_id` to the raw filename stem, but `SourceLine.scene_id`/`line_id` require the `HumanReadableId` pattern (`^[a-z]+(?:_[0-9]+)+$`), so KSRE-style names with hyphens fail validation.
- **Evidence:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py:98` now uses `self.normalize_scene_id(script_path.stem)` and `tests/unit/benchmark/eval_sets/test_parser.py:166` verifies KSRE-style auto-normalization (`scene_id == "scriptasunday_1"`).
- **Impact:** Parser now accepts KSRE-style filenames without manual `scene_id` overrides.
- **Solution:** Implemented via `normalize_scene_id` and regression tests.
- **Files affected:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py`, `tests/unit/benchmark/eval_sets/test_parser.py`

- **Task:** Task 3
- **Status:** resolved
- **Problem:** Committed manifest hashes are placeholder empty-file SHA-256 values (`e3b0...`) and do not match real KSRE script contents, so runtime hash validation fails immediately.
- **Evidence:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:6` stores `e3b0...`; `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:92` enforces equality. Repro command output: `expected=e3b0...`, `actual=3b287fc5137494cfaaf8ff370554ac084ee48651b9026e2abd105e64770db446`, `MISMATCH`. End-to-end repro via loader+downloader raises `ValueError: Hash validation failed for script-a1-sunday.rpy`.
- **Impact:** Benchmark eval-set download path is not runnable with committed Task 3 artifacts.
- **Solution:** Downloaded real KSRE scripts and computed their SHA-256 hashes. Updated manifest.json with real hashes: script-a1-sunday.rpy (3b287fc5...), script-a1-monday.rpy (082dacbe...), script-a2-emi.rpy (fe9f3c25...). Existing test `test_demo_slice_contains_required_content_types` validates hash validation by downloading and parsing the demo slice.
- **Resolution:** do-task round 3 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py`, `tests/unit/benchmark/eval_sets/test_loader.py`

- **Task:** Task 3
- **Status:** resolved
- **Problem:** The committed `demo` slice does not satisfy the task contract requiring dialogue, narration, choices, and multiple speakers.
- **Evidence:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:8` defines `[1, 30]` for `script-a1-sunday.rpy`. Parsing lines 1-30 of the upstream script with `RenpyDialogueParser` produced `parsed_lines=5`, `narration=5`, `speakers=[]`, `menu_choices=0`.
- **Impact:** The configured demo slice cannot exercise the intended parser/aligner/judge behaviors for mixed content types.
- **Solution:** Analyzed KSRE scripts to find suitable content. script-a1-monday.rpy lines 550-649 contains 26 parseable lines with dialogue, narration, 2 menu choices, and multiple speakers (hi, mu). Updated slices.json to use this range. Added comprehensive test `test_demo_slice_contains_required_content_types` that downloads the slice, parses it, and asserts presence of dialogue, narration, choices, and ≥2 named speakers.
- **Resolution:** do-task round 3 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json`, `tests/unit/benchmark/eval_sets/test_loader.py`
