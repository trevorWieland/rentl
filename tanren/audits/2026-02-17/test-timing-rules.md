---
standard: test-timing-rules
category: testing
score: 62
importance: High
violations_count: 4
date: 2026-02-18
status: violations-found
---

# Standards Audit: Test Timing Rules

**Standard:** `testing/test-timing-rules`
**Date:** 2026-02-18
**Score:** 62/100
**Importance:** High

## Summary

The repository has a three-tier test layout and marker conventions, but timing enforcement is only loosely configured in practice. Critical overruns exist in quality test settings and the local execution commands permit higher limits than the standard allows, and some unit tests are located outside the governed `tests/` tree with no tier marker. Without enforcement of `--durations=0` and strict ceilings, fast regressions can slip in without being flagged.

## Violations

### Violation 1: Quality test execution allows 90s per test where the standard requires <30s

- **File:** `tests/quality/pipeline/test_golden_script_pipeline.py:35`
- **Severity:** High
- **Evidence:**
  ```python
  # 90s timeout per scenario --- pipeline tests chain multiple sequential LLM calls
  # (translate requires 2+ round-trips at up to 10s each, plus ingest/export overhead)
  pytestmark = pytest.mark.timeout(90)
  ```
- **Recommendation:** Replace the per-test override with a limit below 30 seconds (for example `pytest.mark.timeout(20)`), then split remaining setup/infrastructure into separate faster tests if needed.

### Violation 2: Quality timeout is explicitly set to the absolute 30s boundary in another quality suite

- **File:** `tests/quality/agents/test_pretranslation_agent.py:40`
- **Severity:** High
- **Evidence:**
  ```python
  pytestmark = [
      pytest.mark.quality,
      pytest.mark.timeout(30),
  ]
  ```
- **Recommendation:** Use a strict budget below 30 seconds (e.g., 25---28s) and/or move expensive fixtures/IO to faster setup-level scopes; preserve deterministic failure with lower `timeout` and explicit timeout-based assertions if needed.

### Violation 3: Makefile tier targets use permissive/incorrect per-tier timeout caps

- **File:** `Makefile:69`, `Makefile:74`, `Makefile:79`
- **Severity:** High
- **Evidence:**
  ```make
  $(call run_test, uv run pytest tests/unit -q --tb=short --timeout=1 ...
  $(call run_test, uv run pytest tests/integration -q --tb=short --timeout=5 ...
  $(call run_test, bash -c '... uv run pytest tests/quality -q --tb=short --timeout=90' ...
  ```
- **Recommendation:** Tighten unit timeout to enforce <250ms and, ideally, avoid blanket per-test hard timeouts by using `pytest-timeout` with explicit budgets only where justified; set integration below 5s and quality below 30s. Use `--durations=0` and markers (`-m unit`, etc.) to surface slow tests per tier.

### Violation 4: Package-local tests are outside governed test discovery and lack tier markers

- **File:** `pyproject.toml:67`, `packages/rentl-core/tests/unit/core/test_explain.py:1`
- **Severity:** Medium
- **Evidence:**
  ```toml
  testpaths = ["tests"]
  ```
  ```python
  """Unit tests for phase explanation module."""
  from __future__ import annotations

  import pytest
  ```
  ```text
  packages/rentl-core/tests/unit/core/test_explain.py
  packages/rentl-core/tests/unit/core/test_help.py
  packages/rentl-core/tests/unit/core/test_migrate.py
  ```
- **Recommendation:** Move these tests into the repository `tests/unit/...` tree or add a dedicated package `conftest.py` that applies `pytestmark = pytest.mark.unit` for `packages/.../tests/unit` and include them in the tiered execution strategy. This ensures timing enforcement applies consistently.

## Compliant Examples

- `tests/unit/conftest.py:5` - Applies `pytest.mark.unit` across the unit tier directory.
- `tests/integration/conftest.py:20` - Applies `pytest.mark.integration` across the integration tier directory.
- `tests/quality/conftest.py:8` - Applies `pytest.mark.quality` across the quality tier directory.

## Scoring Rationale

- **Coverage:** Approximately 75% of tier folders are well-marked (`tests/unit`, `tests/integration`, `tests/quality`), but enforcement is incomplete due command-level and policy exceptions plus ungoverned tests in `packages/rentl-core/tests`.
- **Severity:** High-severity issues are present in both quality and make-target time budgeting; they can allow slow tests to pass without refactor and weaken fast feedback.
- **Trend:** The codebase has active attempts at tiering and timeout-awareness, but there are explicit hardcoded exceptions and outliers still present.
- **Risk:** Medium-to-high: local/test-gate runtimes can drift above target without being treated as violations, increasing feedback lag and hiding performance regressions.
