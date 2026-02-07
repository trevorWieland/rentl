# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

## Signpost 1: RunConfig requires all config sections in tests

**Task:** Task 2 (Core Doctor Diagnostics Module)

**Problem:** Test TOML config fixtures fail validation because RunConfig requires logging, concurrency, retry, and cache sections in addition to project, endpoint, and pipeline.

**Evidence:**
```
Status: fail
Message: Config validation error: 5 validation errors for RunConfig
```

Test case `test_config_valid_pass` creates a minimal TOML with only project, endpoint, and pipeline sections, but RunConfig schema requires:
- `logging` (required)
- `concurrency` (required)
- `retry` (required)
- `cache` (required)

**Tried:** Adding fields incrementally to mock_config fixture in Python tests (this works for Python-based tests)

**Solution:** Test TOML strings in `test_doctor.py` need to include all required sections:

```toml
[logging]
sinks = [{ type = "console" }]

[concurrency]
max_parallel_requests = 8
max_parallel_scenes = 4

[retry]
max_retries = 3
backoff_s = 1.0
max_backoff_s = 30.0

[cache]
enabled = false

[pipeline]
# Must have all 7 phases and default_model
[pipeline.default_model]
model_id = "test/model"

[[pipeline.phases]]
phase = "ingest"
# ... (all 7 phases required)
```

**Files affected:**
- tests/unit/core/test_doctor.py (lines 169-235, 443-473, 525-555, 571-601)

**Status:** Partially fixed in Python fixture, TOML fixtures need updating in follow-up task


## Signpost 2: `run_doctor()` currently mixes warning quality and exit-code category

**Task:** Task 2 (Core Doctor Diagnostics Module)

**Problem:** Two behavior gaps were found in `run_doctor()` aggregation:
1) WARN result for missing runtime has no actionable fix suggestion.
2) LLM connectivity failures are categorized as `ExitCode.CONFIG_ERROR` instead of connection-category exit code.

**Evidence:**

Code paths:
- `packages/rentl-core/src/rentl_core/doctor.py:434-439` sets WARN with `fix_suggestion=None`.
- `packages/rentl-core/src/rentl_core/doctor.py:446-449` maps any failure to `ExitCode.CONFIG_ERROR`.

Reproduction output:
```bash
$ python - <<'PY' ... run_doctor(valid_config, runtime=None) ... PY
llm_status= warn
llm_fix= None

$ python - <<'PY' ... run_doctor(valid_config, runtime=mock_runtime_with_failed_connection) ... PY
overall_status= fail
exit_code= 10
llm_status= fail
```

**Impact:** Future CLI wiring can emit misleading diagnostics: warned checks without remediation text and connectivity failures reported as config failures, which breaks operator triage and weakens exit-code semantics.

## Signpost 3: Exit-code precedence misclassifies mixed failures as connection errors

**Task:** Task 2 (Core Doctor Diagnostics Module)

**Problem:** `run_doctor()` currently chooses `ExitCode.CONNECTION_ERROR` whenever the LLM check fails with a non-`config invalid` message, even if config checks also failed (for example, missing API keys).

**Evidence:**

Code path:
- `packages/rentl-core/src/rentl_core/doctor.py:458-471` only inspects `LLM Connectivity` failure text to pick the exit code.

Reproduction output:
```bash
$ python - <<'PY' ... run_doctor(valid_config, runtime=AsyncMock(...)) with TEST_KEY unset ... PY
overall_status fail
exit_code 30
API Keys fail Missing API keys: TEST_KEY
LLM Connectivity fail 1/1 endpoint(s) failed: test
```

**Impact:** CLI exit code indicates external connectivity (`30`) while a configuration prerequisite failed (`API Keys`). This weakens operator triage and can route remediation to the wrong category.


## Signpost 4: Help registry can drift from real CLI flags

**Task:** Task 4 (Core Help Content Module)

**Problem:** `run-pipeline` help text advertises a flag and usage pattern that the CLI does not accept.

**Evidence:**

Help registry uses a nonexistent plural flag and comma-separated value:
- `packages/rentl-core/src/rentl_core/help.py:120`
  ```python
  "--target-languages LANGS  Target language codes (comma-separated)",
  ```
- `packages/rentl-core/src/rentl_core/help.py:124`
  ```python
  "rentl run-pipeline --target-languages en,es",
  ```

Actual CLI option is singular and repeatable:
- `services/rentl-cli/src/rentl_cli/main.py:163`
  ```python
  None, "--target-language", "-t", help="Target language code (repeatable)"
  ```
- `services/rentl-cli/src/rentl_cli/main.py:504`
  ```python
  target_languages: list[str] | None = TARGET_LANGUAGE_OPTION,
  ```

**Impact:** `rentl help run-pipeline` will mislead users into running an invalid flag, increasing avoidable command failures and weakening trust in CLI diagnostics.


## Signpost 5: Export help still advertises wrong `--column-order` usage

**Task:** Task 4 (Core Help Content Module)

**Problem:** The help registry describes `export --column-order` as comma-separated input, but the real CLI option is repeatable.

**Evidence:**

Help registry currently says comma-separated:
- `packages/rentl-core/src/rentl_core/help.py:95`
  ```python
  "--column-order           Comma-separated column order",
  ```

Actual CLI option is repeatable:
- `services/rentl-cli/src/rentl_cli/main.py:145`
  ```python
  None, "--column-order", help="Explicit CSV column order (repeatable)"
  ```

**Impact:** `rentl help export` can steer users toward malformed `--column-order` input, creating avoidable export errors and another source-of-truth drift between CLI behavior and help docs.
