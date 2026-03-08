---
standard: address-deprecations-immediately
category: global
score: 84
importance: High
violations_count: 2
date: 2026-02-17
status: violations-found
---

# Standards Audit: Address Deprecations Immediately

**Standard:** `global/address-deprecations-immediately`
**Date:** 2026-02-17
**Score:** 84/100
**Importance:** High

## Summary

The codebase avoids explicit deprecated APIs in its own Python sources (e.g., `datetime.utcnow()` was not found in non-venv files), and datetime handling is mostly UTC-aware. The main compliance gap is that deprecation warnings are not consistently treated as test/CI failures, so future deprecations can be introduced or ignored. This is a moderate to high process risk because the standard requires prevention, not detection later.

## Violations

### Violation 1: Pytest configuration does not fail on deprecation warnings

- **File:** `pyproject.toml:71`
- **Severity:** High
- **Evidence:**
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  asyncio_mode = "auto"
  asyncio_default_fixture_loop_scope = "function"
  timeout = 30
  addopts = "-v --tb=short"
  ```
- **Recommendation:** Configure pytest deprecation escalation in project config, for example:
  ```toml
  addopts = "-v --tb=short -W error::DeprecationWarning -W error::PendingDeprecationWarning"
  # or
  filterwarnings = ["error::DeprecationWarning", "error::PendingDeprecationWarning"]
  ```

### Violation 2: Local verification/test commands do not pass deprecation warnings as errors

- **File:** `Makefile:69`
- **Severity:** Medium
- **Evidence:**
  ```make
  unit:
  	@echo "🧪 Running unit tests with coverage..."
  	$(call run_test, uv run pytest tests/unit -q --tb=short --timeout=1 --cov=packages --cov=services --cov-fail-under=80 --cov-precision=2, .unit.log, Unit Tests)
  
  integration:
  	@echo "🔌 Running integration tests..."
  	$(call run_test, uv run pytest tests/integration -q --tb=short --timeout=5, .integration.log, Integration Tests)

  quality:
  	@echo "💎 Running quality tests..."
  	$(call run_test, bash -c 'set -a && [ -f .env ] && source .env && set +a && uv run pytest tests/quality -q --tb=short --timeout=90', .quality.log, Quality Tests)

  test:
  	@uv run pytest --cov=packages --cov=services --cov-report=term-missing
  ```
- **Recommendation:** Add deprecation warning escalation to every pytest invocation used in CI/local gates (for example `-W error::DeprecationWarning`) so deprecation warnings fail runs immediately.

## Compliant Examples

- `services/rentl-cli/src/rentl/main.py:15` — Uses `from datetime import UTC, datetime` and then `datetime.now(UTC)`.
- `packages/rentl-core/src/rentl_core/status.py:7` — Uses `from datetime import UTC, datetime`.
- `packages/rentl-core/src/rentl_core/status.py:163` — Uses `datetime.now(tz=UTC)` instead of UTC-naive/timezone-deprecated patterns.

## Scoring Rationale

- **Coverage:** Source-level deprecation API usage is largely clean, but deprecation-policy enforcement is only partially implemented.
- **Severity:** High severity for the missing pytest warning policy because it allows deprecated APIs to accumulate without hard failures.
- **Trend:** Recent files generally use timezone-safe datetime patterns (`UTC`, `datetime.now(...)`), indicating improving API hygiene, but testing gates remain outdated.
- **Risk:** Medium-to-high operational risk: deprecation warnings can become runtime failures when dependencies or Python versions tighten behavior.
