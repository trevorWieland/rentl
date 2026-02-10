# Signposts

- **Task:** Task 3
- **Status:** unresolved
- **Problem:** `RenpyDialogueParser` defaults `scene_id` to the raw filename stem, but `SourceLine.scene_id`/`line_id` require the `HumanReadableId` pattern (`^[a-z]+(?:_[0-9]+)+$`), so KSRE-style names with hyphens fail validation.
- **Evidence:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py:38` sets `scene_id = script_path.stem`, and `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py:51` builds `line_id=f"{scene_id}_{self.line_counter}"`. Repro output:
  - `ValidationError`
  - `line_id ... input_value='script-a1-sunday_1'`
  - `scene_id ... input_value='script-a1-sunday'`
- **Impact:** End-to-end parsing fails on real Katawa Shoujo filenames unless callers manually override `scene_id`, which blocks reliable alignment and benchmark execution.
- **Solution:** Add deterministic ID normalization from filename -> schema-valid `scene_id` and matching `line_id` generation, with regression coverage for KSRE-style filenames.
- **Files affected:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py`, `tests/unit/benchmark/eval_sets/test_parser.py`
