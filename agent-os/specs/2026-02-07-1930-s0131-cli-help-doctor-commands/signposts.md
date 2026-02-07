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
