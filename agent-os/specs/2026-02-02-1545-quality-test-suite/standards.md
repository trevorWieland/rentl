# Standards for Quality Test Suite

The following standards apply to this work.

---

## testing/three-tier-test-structure

# Three-Tier Test Structure

All tests live under `tests/unit`, `tests/integration`, or `tests/quality`. No exceptions.

```
tests/
├── unit/           # <250ms per test, mocks only, no external services
│   ├── core/
│   ├── cli/
│   └── tui/
├── integration/    # <5s per test, minimal mocks, real services, NO LLMs
│   ├── core/
│   ├── cli/
│   └── tui/
└── quality/        # <30s per test, minimal mocks, real services, REAL LLMs
    ├── core/
    └── cli/
```

**Tier definitions:**

**Unit tests** (`tests/unit/`):
- Fast: <250ms per test
- Mocks allowed and encouraged
- No external services (no network, no LLMs, no databases)
- Test isolated logic and algorithms

**Integration tests** (`tests/integration/`):
- Moderate speed: <5s per test
- Minimal mocks (only when unavoidable)
- Real services (storage, vector store, file system)
- **NO LLMs** - use mock model adapters for LLM calls
- BDD-style (Given/When/Then)

**Quality tests** (`tests/quality/`):
- Slower but bounded: <30s per test
- Minimal mocks (only when unavoidable)
- Real services (storage, vector store, file system)
- **REAL LLMs** - actual model calls, not mocked
- BDD-style (Given/When/Then)

**Package structure mirrors source:**
- `tests/unit/core/` tests `rentl_core/`
- `tests/integration/cli/` tests `rentl_cli/`
- Etc.

**Never place tests:**
- Outside the three tier folders
- In source code directories
- In ad-hoc locations (scripts, benchmarks, etc.)

**CI execution:**
- Unit tests: Run on every PR, fast feedback
- Integration tests: Run on every PR or schedule
- Quality tests: Run on schedule or manual trigger (slower)

**Why:** Clear purpose and scope for each test tier, and enables selective execution by tier (unit fast/run frequently, integration/quality slower/run selectively).

---

## testing/bdd-for-integration-quality

# BDD for Integration & Quality Tests

Integration and quality tests must use BDD-style (Given/When/Then). Unit tests can use direct assertions.

```python
# ✓ Good: BDD-style for integration/quality tests
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

# Integration tests: Use mock model adapter (no real LLMs)
# Quality tests: Use real model adapter (actual LLMs)

# ✗ Bad: Direct assertions in integration/quality tests
def test_pipeline_completion():
    pipeline = setup_pipeline()
    result = await pipeline.run()
    assert result.success is True  # Not BDD-style
```

**BDD structure:**

**Given:** Setup test state
- Arrange test data and fixtures
- Configure system under test
- Document preconditions

**When:** Perform action
- Execute the behavior being tested
- Single action or small sequence
- Document trigger

**Then:** Verify outcome
- Assert expected results
- Validate post-conditions
- Document expected behavior

**Integration tests:**
- BDD-style required
- Real services (storage, vector store, file system)
- Mock model adapters (NO real LLMs)
- <5s per test

**Quality tests:**
- BDD-style required
- Real services (storage, vector store, file system)
- Real model adapters (REAL LLMs)
- <30s per test

**Unit tests:**
- Direct assertions allowed (no BDD requirement)
- Focus on isolated logic
- <250ms per test

**BDD benefits:**
- Tests read like documentation/specs
- Easier to understand for new developers
- Focuses on behavior and scenarios, not implementation
- Clear Given/When/Then structure

**Example scenario:**

```gherkin
Scenario: Pipeline translates scene with context
  Given a configured pipeline with sample script
    And context layer with character definitions
  When the pipeline runs to completion
  Then the pipeline produces a playable patch
    And translations respect character consistency
```

**Never use BDD for:**
- Unit tests (direct assertions are fine)
- Performance benchmarks (different format)
- One-off validation scripts

**Why:** Tests read like documentation/specs (easier to understand) and focuses on behavior and scenarios instead of implementation details.

---

## testing/no-mocks-for-quality-tests

# No Mocks for Quality Tests

Quality tests use real LLMs (actual model calls). Integration tests must mock LLMs.

```python
# ✓ Good: Quality test with real LLM
# tests/quality/core/translation.py
from rentl_core.adapters.model.openai_client import OpenAIClient

async def test_translation_quality_with_real_llm(given_translation_request):
    """Test translation quality with actual model call."""
    client = OpenAIClient(base_url="https://api.openai.com/v1", api_key="test-key")
    result = await client.translate(given_translation_request)

    # Validate actual model output, not mocked response
    assert result.text is not None
    assert len(result.text) > 0
    assert result.model == "gpt-4"

# ✓ Good: Integration test with mocked LLM
# tests/integration/core/translation.py
from unittest.mock import AsyncMock

async def test_translation_flow(given_translation_request):
    """Test translation flow with mocked LLM (no real calls)."""
    mock_client = AsyncMock()
    mock_client.translate.return_value = TranslationResult(text="mocked text", model="gpt-4")

    result = await mock_client.translate(given_translation_request)
    assert result.text == "mocked text"  # Verify mock, not real model

# ✗ Bad: Quality test with mocked LLM
async def test_translation_quality(given_translation_request):
    """Quality test must NOT mock LLM."""
    mock_client = AsyncMock()
    mock_client.translate.return_value = TranslationResult(text="mocked text")
    # This validates mock, not real model behavior - FAILS QA PURPOSE
```

**Quality tests:**
- **REAL LLMs** - actual model calls, not mocked
- BDD-style (Given/When/Then)
- Real services (storage, vector store, file system)
- Minimal mocks (only when unavoidable)
- <30s per test
- Validates actual model behavior and quality, not mocked responses

**Integration tests:**
- **NO LLMs** - mock model adapters for LLM calls
- BDD-style (Given/When/Then)
- Real services (storage, vector store, file system)
- Minimal mocks (only when unavoidable)
- <5s per test
- Tests pipeline flow, not model behavior

**Why real LLMs in quality tests:**
- Validates actual model behavior and quality
- Catches regressions when models change or update
- Ensures prompts and schemas work with real models
- Tests error handling for real API responses

**Why mock LLMs in integration tests:**
- Fast feedback (<5s vs <30s)
- Avoids LLM API rate limits and costs
- Tests pipeline flow, not model behavior
- Makes integration tests deterministic and fast

**Never mock LLMs for:**
- Quality tests (defeats purpose)
- Validating model-specific behavior
- Testing prompt engineering effectiveness
- Validating actual translation quality

**Never use real LLMs for:**
- Unit tests (should be <250ms)
- Integration tests (should be <5s)

**API key management for quality tests:**
- Use test API keys with rate limits
- Cache LLM responses when possible (within <30s bound)
- Document API key setup in test docs
- CI should have API key configured for quality tier

**Why:** Validates actual model behavior and quality, not mocked responses; ensures prompts and schemas work with real models and tests error handling for real API responses.

---

## testing/test-timing-rules

# Test Timing Rules

Enforce strict timing limits per tier. Tests exceeding limits must be rewritten.

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (<250ms)",
    "integration: Integration tests (<5s)",
    "quality: Quality tests (<30s)",
]

# CI configuration
# pytest -m unit --durations=0  # Show slowest unit tests
# pytest -m integration --durations=0  # Show slowest integration tests
# pytest -m quality --durations=0  # Show slowest quality tests
```

**Timing limits:**

**Unit tests:** <250ms per test
- Isolated logic and algorithms only
- No external services (network, I/O, databases)
- If test exceeds 250ms, it's not a unit test - move to integration or refactor

**Integration tests:** <5s per test
- Real services (storage, vector store, file system)
- Minimal mocks
- If test exceeds 5s, it's doing too much - split into multiple tests or optimize

**Quality tests:** <30s per test
- Real LLMs (actual model calls)
- Real services (storage, vector store, file system)
- If test exceeds 30s, it's doing too much - split into multiple tests or use cached results

**Enforcement:**

**CI:**
- Fail tests that exceed timing limits
- Use `--durations=0` to flag slow tests
- Block PRs that introduce slow tests

**Locally:**
- Run `pytest --durations=0` to identify slow tests
- Refactor or split slow tests immediately
- Don't ignore timing warnings

**Refactoring strategies:**
- Split large tests into smaller, focused tests
- Cache expensive operations (setup, data loading)
- Remove unnecessary external service calls
- Optimize test data (smaller datasets, fewer iterations)

**Never:**
- Ignore timing warnings or failures
- Comment out slow tests instead of fixing
- Add `@pytest.mark.slow` as loophole (no such marker exists)

**Why:** Fast feedback loop - failing tests identified quickly, prevents test suite from becoming slow and painful to run.

---

## testing/mandatory-coverage

# Mandatory Coverage

Coverage is mandatory for features. Tests must directly exercise intended behavior.

```python
# ✓ Good: Tests exercise actual behavior
# tests/unit/core/translator.py
async def test_translates_scene_with_context(given_scene, given_context):
    """Test that translation applies context to output."""
    result = await translate_scene(given_scene, given_context)
    
    # Directly exercises translation behavior
    assert "character_name" in result.text
    assert result.context_used == given_context.id

# ✗ Bad: Tests don't exercise behavior
async def test_translator_initialization():
    """Just tests constructor, not behavior - NO COVERAGE VALUE."""
    translator = Translator()
    assert translator is not None  # No behavior tested
```

**Coverage requirements:**

**For every feature:**
- Tests must directly exercise intended behavior
- All code paths must be covered (happy path, error cases, edge cases)
- No uncovered production code
- Coverage must pass in CI before merging

**CI enforcement:**
- Run `pytest --cov=rentl_core --cov=rentl_cli --cov=rentl_tui`
- Fail PRs below coverage threshold (e.g., 80%)
- Block merging new features without tests
- Generate coverage reports for review

**What counts as coverage:**

**✓ Direct behavior testing:**
- Unit tests calling functions with real inputs
- Integration tests running full workflows
- Quality tests validating end-to-end behavior
- Error path and edge case testing

**✗ NOT coverage:**
- Constructor-only tests (no behavior)
- Property access tests (no behavior)
- Mock-only tests (no real logic)
- Tests that bypass or stub out production code

**Coverage strategies:**

**Unit tests:**
- Test isolated functions and methods
- Mock external dependencies
- Cover all branches and error paths
- Use parametrization for edge cases

**Integration tests:**
- Test workflows and component interaction
- Use real services (storage, vector store)
- Cover cross-component code paths
- Validate end-to-end behavior

**Quality tests:**
- Test with real LLMs
- Validate actual outputs, not mocks
- Cover model integration paths
- Ensure prompt/response handling

**Never merge:**
- New features without tests
- Tests that don't exercise behavior
- Uncovered code paths
- Failing coverage checks in CI

**Why:** Catches regressions early by testing actual behavior; ensures code quality and test hygiene by preventing untested production code.

---

## testing/no-test-skipping

# No Test Skipping

Never skip tests within a tier. Tests either run and pass or run and fail.

```python
# ✓ Good: Test runs and passes or runs and fails
async def test_translation_with_context(given_scene, given_context):
    """Test runs and validates result."""
    result = await translate_scene(given_scene, given_context)
    
    if result.success:
        assert "character_name" in result.text
    else:
        raise AssertionError(f"Translation failed: {result.error}")  # Test fails

# ✗ Bad: Skip test instead of fixing
import pytest

@pytest.mark.skip(reason="Flaky test, will fix later")  # NEVER DO THIS
async def test_translation_with_context(given_scene, given_context):
    result = await translate_scene(given_scene, given_context)
    assert "character_name" in result.text
```

**Test execution philosophy:**

**Within a tier:**
- Tests either run and pass ✓
- Or run and fail ✗
- Never skip or bypass

**Tier-level execution:**
- Run full unit tier with zero skips
- Run full integration tier with zero skips
- Run full quality tier with zero skips

**No skipping means:**

**No `@pytest.mark.skip`:**
- No "will fix later" skips
- No flaky test skips
- No platform-specific skips (fix test or skip entire tier)
- No configuration skips (make tests work with all configs)

**No conditionals that skip tests:**
- No `if not has_feature: pytest.skip()`
- No `if not on_platform: pytest.skip()`
- No `if not has_credentials: pytest.skip()`

**No CI-level skips:**
- Don't skip test tiers in CI
- Don't skip tests based on conditions
- Run all tiers with `--no-skips` flag

**When tests fail:**

**Fix the test or fix the code:**
- If test is wrong: fix the test
- If code is broken: fix the code
- If test is flaky: make it deterministic or delete it

**Never:**
- Skip failing tests
- Comment out failing tests
- Use `@pytest.mark.xfail` as loophole

**Why tests fail:**

**Flaky tests:**
- Make deterministic (remove randomness, fix race conditions)
- Use explicit setup/teardown
- Delete test if can't be made reliable

**Platform-specific:**
- Fix test to work across platforms or skip entire tier on incompatible platforms
- Document platform-specific behavior in test name, don't skip individual tests

**Configuration-specific:**
- Make tests work with all configurations
- Test multiple configs if needed
- Don't skip based on config state

**CI enforcement:**

**Fail CI on skips:**
- Block PRs that introduce test skips
- Fail entire CI run if any test is skipped
- Use `pytest --no-skips` to ensure no bypass

**Alert on skips:**
- CI should fail loudly if tests are skipped
- Require explicit override to merge with skips (extremely rare)

**Never:**
- Use test skips as bandage for broken tests
- "Will fix later" mentality
- Silent test bypasses

**Why:** Tests either work or fail; no silent bypasses ensures test suite is reliable and trustworthy; prevents accumulation of broken/flaky tests.

---

## testing/make-all-gate

# Make All Gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands
