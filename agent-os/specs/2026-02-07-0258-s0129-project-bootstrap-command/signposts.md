# Signposts

- **Task:** Task 2
- **Problem:** The test change validates parsing without `[agents]`, but it does not verify runtime fallback to package defaults, leaving the new `agents=None` branch untested.
- **Evidence:** `tests/unit/cli/test_main.py:367` only executes `config = cli_main._load_resolved_config(config_path)` and `assert config.agents is None`. The new runtime branch is in `packages/rentl-agents/src/rentl_agents/wiring.py:1124`. Coverage on wiring tests reports this branch unexecuted: `Missing ... 1125-1126` from `pytest -q tests/unit/rentl-agents/test_wiring.py --cov=rentl_agents.wiring --cov-report=term-missing --cov-fail-under=0`.
- **Impact:** Future tasks relying on generated configs without `[agents]` can regress at runtime even when schema/CLI parsing tests pass.

- **Task:** Task 3
- **Problem:** `InitAnswers` accepts `input_format="tsv"`, but generated `rentl.toml` cannot validate against `RunConfig`, violating the generated-config contract.
- **Evidence:** `packages/rentl-core/src/rentl_core/init.py:43` types `input_format` as unconstrained `str`, and `packages/rentl-core/src/rentl_core/init.py:226` explicitly treats `"tsv"` as supported seed output. `RunConfig` only allows `FileFormat` values `csv|jsonl|txt` (`packages/rentl-schemas/src/rentl_schemas/primitives.py:84`). Repro output from audit:
  `ValidationError: project.formats.input_format Value error, 'tsv' is not a valid FileFormat` and
  `ValidationError: project.formats.output_format Value error, 'tsv' is not a valid FileFormat`.
- **Impact:** Future CLI work (`rentl init`) can scaffold projects that fail immediately at config validation, creating a broken first-run path.

- **Task:** Task 4
- **Problem:** `rentl init` cancellation currently throws instead of exiting cleanly, and the task shipped without the required CLI tests.
- **Evidence:** In `services/rentl-cli/src/rentl_cli/main.py:211`, cancel path raises `typer.Exit(code=ExitCode.SUCCESS.value)`, but broad handler at `services/rentl-cli/src/rentl_cli/main.py:290` catches it as `Exception` and calls `_error_from_exception()`. Repro from audit:
  `exit_code= 1`
  `exception= ValidationError`
  `exception_msg= 1 validation error for ErrorResponse ... String should have at least 1 character`.
  Test coverage gap evidence: `rg -n "\\binit\\b|rentl init|test_.*init" tests/unit/cli/test_main.py` returned `NO_MATCH`.
- **Impact:** Declining overwrite for an existing `rentl.toml` produces a failure path instead of a safe cancel, and missing regression tests leaves this path vulnerable to future breakage.

- **Task:** Task 4
- **Problem:** `rentl init` accepts malformed comma-separated target language input (for example `en,`) and can scaffold an invalid config while still exiting successfully.
- **Evidence:** CLI parsing in `services/rentl-cli/src/rentl_cli/main.py:227` uses `target_languages = [lang.strip() for lang in target_languages_input.split(",")]`, which keeps empty items. Audit repro:
  `exit_code=0`
  `validate_run_config=FAIL`
  `ValidationError: project.languages.target_languages.1 String should match pattern '^[a-z]{2}(?:-[A-Z]{2})?$'`.
  Current tests in `tests/unit/cli/test_main.py:1452` and `tests/unit/cli/test_main.py:1497` only exercise default `"en"` and do not cover malformed comma-separated input.
- **Impact:** This violates the non-negotiable generated-config contract and can leave first-time users with a project that fails at config validation despite a successful `rentl init`.

- **Task:** Task 5
- **Problem:** Seed data generation produced invalid IDs and field names that violated `SourceLine` schema, causing ingestion to fail.
- **Evidence:** Integration test revealed three validation failures in `packages/rentl-core/src/rentl_core/init.py:219-236`:
  1. `line_id` used `"001"` instead of pattern `^[a-z]+(?:_[0-9]+)+$` (needed `"line_001"`)
  2. `route_id` used `"main"` instead of pattern `^[a-z]+(?:_[0-9]+)+$` (needed `"route_001"`)
  3. Field name was `"original_text"` but `SourceLine` schema requires `"text"`
  Test output: `ValidationError: 3 validation errors for SourceLine`
- **Tried:** Created integration test `tests/integration/cli/test_init.py` that validates seed data against `SourceLine` schema. This caught the bug immediately.
- **Solution:** Fixed seed data generation for both JSONL and CSV formats to use correct ID patterns (`line_001`, `route_001`, `scene_001`) and correct field name (`text`). Updated unit tests in `tests/unit/core/test_init.py` that were checking for the wrong field name.
- **Files affected:** `packages/rentl-core/src/rentl_core/init.py:219-236`, `tests/integration/cli/test_init.py` (new), `tests/integration/features/cli/init.feature` (new), `tests/unit/core/test_init.py:148-196`
