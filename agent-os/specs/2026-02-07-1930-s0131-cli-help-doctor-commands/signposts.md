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

