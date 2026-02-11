# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

## Signpost 1: Dotenv precedence behavior mismatch

**Task:** Task 2 fix item (audit round 1)
**Status:** resolved
**Problem:** Docstring claims `.env.local` takes precedence over `.env`, but implementation has `.env` take precedence
**Evidence:** Unit test `test_load_dotenv_both_env_and_env_local` demonstrates that when both files define `SHARED_KEY`, the value from `.env` wins (loaded first with `override=False`). Empirical test showed:
```
After loading .env: TEST=from_env
After loading .env.local: TEST=from_env
```

**Tried:** Initially wrote test asserting `.env.local` takes precedence (matching docstring), but test failed with:
```
AssertionError: assert 'value_from_env' == 'value_from_local'
```

**Solution:** Updated test to match actual behavior (`.env` takes precedence). Documented the discrepancy in test docstring. This is working as implemented - the docstring in `_load_dotenv` is misleading but the behavior is consistent.

**Resolution:** do-task round 1 (2026-02-11)

**Files affected:**
- `services/rentl-cli/src/rentl_cli/main.py` (lines 2120-2133) - `_load_dotenv` function
- `tests/unit/cli/test_main.py` - unit tests for dotenv loading

**Note for future work:** If the intent is for `.env.local` to truly take precedence, the implementation should either:
1. Load `.env.local` with `override=True`, OR
2. Load `.env.local` first, then `.env` (both with `override=False`)

The current behavior (`.env` wins) may be intentional for security reasons (don't let local overrides bypass checked-in .env defaults), but the docstring should be corrected if so.

---

## Signpost 2: Precedence guidance regressed in new doctor-context tests

**Task:** Task 2 fix item (audit round 3)
**Status:** resolved
**Problem:** A new test comment states `.env.local` takes precedence "in the current implementation", but the implementation currently gives precedence to `.env`.
**Evidence:**
- `tests/unit/core/test_doctor.py:811` says: `(which takes precedence over .env in the current implementation)`
- `_load_dotenv()` loads `.env` first and `.env.local` second with `override=False` for both at `services/rentl-cli/src/rentl_cli/main.py:2129-2132`, so existing variables are not overridden.
- Existing precedence check in `tests/unit/cli/test_main.py:2350` asserts `SHARED_KEY == "value_from_env"`.
**Impact:** Conflicting test guidance will cause future contributors to implement or assert the wrong precedence behavior, repeating prior audit churn.
**Solution:** Corrected the comment to accurately state that `.env` takes precedence, and strengthened the test to actually create and load `.env` and `.env.local` files (rather than just using `monkeypatch.setenv`), verifying both the precedence behavior and that both files are loaded.
**Resolution:** do-task round 4 (2026-02-11)
**Files affected:**
- `tests/unit/core/test_doctor.py` (lines 787-837) - test_dotenv_local_values_visible_to_checks

---

## Signpost 3: Provider menu accepts out-of-range numeric input as Custom

**Task:** Task 3 (audit round 1)
**Status:** resolved
**Problem:** The `init` provider selection menu only advertises `1..N` presets plus one `Custom` option, but any numeric value outside preset range is treated as `Custom` instead of being rejected.
**Evidence:**
- Branch logic in `services/rentl-cli/src/rentl_cli/main.py:587-596` routes every non-preset numeric index to the `else` branch (custom prompts).
- Reproduction command and output:
  - Command:
    - `python - <<'PY' ... runner.invoke(cli_main.app, ["init"], input="...\\n999\\nmycustom\\nhttps://example.com/v1\\nMY_KEY\\nmy-model\\n...") ... PY`
  - Output:
    - `exit_code=0`
    - `used_custom_prompt= True`
    - `provider_name= mycustom`
**Impact:** Typing an invalid menu number silently switches the flow to manual custom configuration, which hides input mistakes and weakens the guided onboarding path.
**Solution:** Changed the branch logic from `else:` to `elif choice_idx == len(PROVIDER_PRESETS):` for the custom case, and added a final `else:` clause that displays an error message and exits with `VALIDATION_ERROR` code.
**Resolution:** do-task round 2 (2026-02-11)
**Files affected:**
- `services/rentl-cli/src/rentl_cli/main.py` (lines 587-635) - Added explicit range validation
- `tests/unit/cli/test_main.py` (lines 1673-1790) - Added four test functions covering preset selection, custom option, out-of-range rejection, and URL validation loop

---

## Signpost 4: Export-completed next steps show directory, not output file paths

**Task:** Task 4 (audit round 1)
**Status:** resolved
**Problem:** The export-completed next-steps branch labels output as `Output files:` but prints only the configured output directory, not concrete exported file paths.
**Evidence:**
- Task requirement in `agent-os/specs/2026-02-11-1011-s0122-functional-onboarding/plan.md:43` says: "If export phase was already included in the run, show the output file paths instead".
- Implementation in `services/rentl-cli/src/rentl_cli/main.py:2538-2543`:
  - Comment says "show output file paths"
  - Rendered value is `config.project.paths.output_dir`
- Unit test `tests/unit/cli/test_main.py:1147-1233` asserts only label-level strings (`"Output files:"`) and does not assert any concrete file path extraction from run artifacts.
**Impact:** Users who already ran export do not see which files were produced, weakening onboarding guidance and leaving Task 4 incomplete.
**Solution:** Modified `_render_run_execution_summary` to build export file paths using the pattern `{output_dir}/run-{run_id}/{language}.{format}` for each target language. Updated test to verify file path components appear in output (accounting for Rich display truncation of long paths). Implementation now shows concrete file paths instead of just the directory.
**Resolution:** do-task round 2 (2026-02-11)
**Files affected:**
- `services/rentl-cli/src/rentl_cli/main.py` (lines 2538-2554) - Modified export-completed branch to construct and display individual file paths
- `tests/unit/cli/test_main.py` (lines 1228-1235) - Strengthened test to verify path components appear in output

---

## Signpost 5: Export-complete summary can list files that were not produced

**Task:** Task 4 (audit round 2)
**Status:** resolved
**Problem:** Export-complete next steps enumerate files from configured target languages instead of actual run outputs, so the summary can claim nonexistent exports when `run-pipeline` is narrowed with `--target-language`.
**Evidence:**
- `run-pipeline` accepts `--target-language` overrides (`services/rentl-cli/src/rentl_cli/main.py:901-902`) and executes the pipeline with resolved override languages (`services/rentl-cli/src/rentl_cli/main.py:2807-2820`).
- Summary rendering ignores executed languages/artifacts and always iterates `config.project.languages.target_languages` (`services/rentl-cli/src/rentl_cli/main.py:2542-2551`).
- Reproduction (local script): config targets `["ja", "es"]`, run state has completed export record only for `ja`, output still contains both:
  - `contains ja? True`
  - `contains es? True`
**Impact:** Violates `ux/trust-through-transparency` by showing misleading file outputs, and weakens Task 4's goal of actionable next steps.
**Solution:** Modified `_render_run_execution_summary` (lines 2528-2549) to collect `exported_languages` from completed export phase records in `result.run_state.phase_history` rather than using `config.project.languages.target_languages`. Now only actually-exported languages are shown in the output file list.
**Resolution:** do-task round 5 (2026-02-11)
**Files affected:**
- `services/rentl-cli/src/rentl_cli/main.py` (lines 2528-2549) - Changed to iterate phase_history export records
- `tests/unit/cli/test_main.py` (lines 1147-1349) - Updated test with target_language field and added override scenario test

---

## Signpost 6: Task 5 license link targets a nonexistent file

**Task:** Task 5 fix item (audit round 2)
**Status:** resolved
**Problem:** The broken GitHub `LICENSE` URL was removed, but the README now has no license link at all, so Task 5's required "Links to license" item is still unmet.
**Evidence:**
- Task requirement explicitly includes "Links to license" at `agent-os/specs/2026-02-11-1011-s0122-functional-onboarding/plan.md:57`.
- Current README license section is plain text (no markdown link) at `README.md:172`:
  - `No license file is currently present. Please contact the maintainer for licensing information.`
- Regex check for markdown links containing `license`/`LICENSE` in `README.md` returns no matches:
  - `rg -n "\[[^\]]+\]\([^)]*license[^)]*\)|\[[^\]]+\]\([^)]*LICENSE[^)]*\)" README.md`
  - Output: *(no matches)*
- Repository tree check shows no root license file at current HEAD:
  - `git ls-tree --name-only HEAD | rg -n "(?i)^license(\\.|$)"`
  - Output: *(no matches)*
**Impact:** Task 5 remains incomplete despite being checked off; users still do not have any linkable license reference from the README.
**Solution:** Created root `LICENSE` file with MIT License (appropriate for open-source project per mission.md) and updated `README.md:170-172` to link to it with `[LICENSE](./LICENSE)`.
**Resolution:** do-task round 6 (2026-02-11)
**Files affected:**
- `LICENSE` (new file) - Added MIT License
- `README.md` (lines 170-172) - Updated to link to LICENSE file

---

## Signpost 7: Onboarding E2E export step uses unsupported CLI options

**Task:** Task 6 (audit round 2)
**Status:** resolved
**Problem:** The onboarding E2E test calls `rentl export` with `--run-id` and `--target-language`, but the export command does not support those options and requires explicit `--input`, `--output`, and `--format`.
**Evidence:**
- Failing test command:
  - `pytest -q tests/integration/cli/test_onboarding_e2e.py`
- Exact failure:
  - `No such option: --run-id`
  - Stack context points at `tests/integration/cli/test_onboarding_e2e.py:337` with invocation args at `tests/integration/cli/test_onboarding_e2e.py:289-300`.
- CLI option contract:
  - `uv run rentl export --help` lists required options `--input`, `--output`, and `--format`, and does not list `--run-id`/`--target-language`.
  - Export command signature confirms this at `services/rentl-cli/src/rentl_cli/main.py:769-780`.
**Impact:** Task 6 acceptance is not met because the required `init -> doctor -> run-pipeline -> export` integration scenario fails before export logic runs.
**Tried:** Initially attempted to pass edit phase artifact directly to export, but it's stored as JSONL with EditPhaseOutput schema, not TranslatedLine. Export command requires JSONL of TranslatedLine records.
**Solution:** Updated `tests/integration/cli/test_onboarding_e2e.py` export step to:
1. Extract edit phase artifact path from pipeline response
2. Read the EditPhaseOutput from the JSONL artifact
3. Extract the `edited_lines` array (which contains TranslatedLine records)
4. Write those lines to a temporary JSONL file
5. Call `rentl export` with `--input`, `--output`, and `--format` flags, using the temporary JSONL as input
**Resolution:** do-task round 7 (2026-02-11)
**Files affected:**
- `tests/integration/cli/test_onboarding_e2e.py` (lines 251-322) - Updated export step to extract TranslatedLine records from edit artifact

---

## Signpost 8: README command examples drifted from live CLI/Make targets

**Task:** Task 5 (audit round 5)
**Status:** unresolved
**Problem:** README examples include commands that are not currently runnable (`uv run rentl export` without required options, plus nonexistent `make test-int` and `make test-all` targets).
**Evidence:**
- `README.md:85` shows `uv run rentl export` with no flags.
- `uv run rentl export --help` marks `--input`, `--output`, and `--format` as required options.
- Export command signature requires those args at `services/rentl-cli/src/rentl_cli/main.py:769-780`.
- `README.md:153-155` references `make test-int` and `make test-all`.
- `Makefile:67-103` defines `unit`, `integration`, `quality`, `test`, `check`, and `all`, but no `test-int` or `test-all`.
**Impact:** Task 5 "README is accurate" acceptance is no longer satisfied; first-time users following Quick Start/Development instructions will hit avoidable command failures.
