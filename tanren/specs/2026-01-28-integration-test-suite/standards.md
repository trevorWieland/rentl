# Standards for Integration Test Suite

The following standards apply to this work.

---

## testing/bdd-for-integration-quality

Integration and quality tests must use BDD-style (Given/When/Then). Unit tests can use direct assertions.

```python
# Good: BDD-style for integration/quality tests
from pytest_bdd import given, when, then, scenarios

@given("a configured pipeline with sample script")
def configured_pipeline(tmp_path):
    return setup_pipeline(tmp_path, sample_script)

@when("the pipeline runs to completion")
async def run_pipeline(configured_pipeline):
    configured_pipeline.result = await configured_pipeline.run()

@then("the pipeline produces a playable patch")
def check_output(configured_pipeline):
    assert configured_pipeline.result.success is True
    assert (configured_pipeline.output_dir / "patch.json").exists()
```

**BDD structure:**

- **Given:** Setup test state (arrange test data and fixtures)
- **When:** Perform action (execute the behavior being tested)
- **Then:** Verify outcome (assert expected results)

**Integration tests:**
- BDD-style required
- Real services (storage, vector store, file system)
- Mock model adapters (NO real LLMs)
- <5s per test

---

## testing/three-tier-test-structure

All tests live under `tests/unit`, `tests/integration`, or `tests/quality`. No exceptions.

```
tests/
├── unit/           # <250ms per test, mocks only, no external services
├── integration/    # <5s per test, minimal mocks, real services, NO LLMs
└── quality/        # <30s per test, minimal mocks, real services, REAL LLMs
```

**Package structure mirrors source:**
- `tests/unit/core/` tests `rentl_core/`
- `tests/integration/cli/` tests `rentl_cli/`

---

## testing/make-all-gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands

---

## testing/mandatory-coverage

Coverage is mandatory for features. Tests must directly exercise intended behavior.

**Coverage requirements:**
- Tests must directly exercise intended behavior
- All code paths must be covered (happy path, error cases, edge cases)
- No uncovered production code
- Coverage must pass in CI before merging

**What counts as coverage:**
- Unit tests calling functions with real inputs
- Integration tests running full workflows
- Quality tests validating end-to-end behavior
- Error path and edge case testing

---

## testing/no-mocks-for-quality-tests

Quality tests use real LLMs (actual model calls). Integration tests must mock LLMs.

**Quality tests:**
- **REAL LLMs** - actual model calls, not mocked
- BDD-style (Given/When/Then)
- <30s per test

**Integration tests:**
- **NO LLMs** - mock model adapters for LLM calls
- BDD-style (Given/When/Then)
- <5s per test
- Tests pipeline flow, not model behavior

---

## architecture/thin-adapter-pattern

Surface layers (CLI, TUI, API, etc.) are **thin adapters only**. All business logic lives in the **Core Domain** packages.

```python
# Good: CLI is a thin wrapper
def run_pipeline(run_id: str):
    """Start pipeline run - thin adapter over core API."""
    result = await pipeline_runner.start_run(run_id)
    return format_json_output(result)
```

**Core Domain logic includes:**
- Pipeline orchestration and phase execution
- Data transformation and validation
- Agent orchestration
- Storage operations
- Model integration

**Surface layers may contain:**
- Command definitions and argument parsing
- Output formatting (pretty-print, JSON wrapper)
- Truly surface-specific features that will never be reused

**Why:** Ensures core logic is reusable across any surface (CLI, TUI, API, Lambda) without duplication and makes testing easier (test core once, surfaces are just IO wrappers).
