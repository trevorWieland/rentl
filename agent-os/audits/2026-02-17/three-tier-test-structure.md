---
standard: three-tier-test-structure
category: testing
score: 84
importance: High
violations_count: 11
date: 2026-02-18
status: violations-found
---

# Standards Audit: Three-Tier Test Structure

**Standard:** `testing/three-tier-test-structure`
**Date:** 2026-02-18
**Score:** 84/100
**Importance:** High

## Summary

The repo is mostly organized under `tests/unit`, `tests/integration`, and `tests/quality`, but it still has tests outside those mandatory roots and one quality test with an overlong timeout. There is also a small subset of integration/quality tests still written in plain pytest style instead of `Given/When/Then` BDD flow. This reduces consistency and weakens the enforceability of tier-specific guarantees (especially discovery + timing rules).

## Violations

### Violation 1: Test files exist outside required tier roots

- **File:** `tests/features/benchmark/eval_set_download.feature:1`
- **Severity:** High
- **Evidence:**
  ```
  Feature: Benchmark Eval Set Download
  As a rentl user
  I want to download and validate eval set source material
  ```
- **Recommendation:** Move this feature file to `tests/integration/benchmark/` or `tests/quality/benchmark/` to align with tier-based placement.

### Violation 2: Test files exist outside required tier roots

- **File:** `tests/features/benchmark/judge_evaluation.feature:1`
- **Severity:** High
- **Evidence:**
  ```
  Feature: LLM Judge Evaluation
  As a benchmark user
  I want to evaluate translations using an LLM judge
  ```
- **Recommendation:** Move this feature file to `tests/integration/benchmark/` or `tests/quality/benchmark/` under the required tier directory.

### Violation 3: Test files exist outside required tier roots

- **File:** `tests/features/benchmark/cli_command.feature:1`
- **Severity:** High
- **Evidence:**
  ```
  Feature: Benchmark CLI Command
  As a rentl user
  I want to run benchmark evaluations via CLI
  ```
- **Recommendation:** Move this feature file to `tests/integration/benchmark/` or `tests/quality/benchmark/`.

### Violation 4: Unit tests stored in source package directory (outside required root)

- **File:** `packages/rentl-core/tests/unit/core/test_explain.py:1`
- **Severity:** High
- **Evidence:**
  ```
  """Unit tests for phase explanation module."""
  from __future__ import annotations
  import pytest
  ```
- **Recommendation:** Relocate to `tests/unit/core/test_explain.py` and remove package-local duplicate from source tree.

### Violation 5: Unit tests stored in source package directory (outside required root)

- **File:** `packages/rentl-core/tests/unit/core/test_help.py:1`
- **Severity:** High
- **Evidence:**
  ```
  """Unit tests for command help module."""
  from __future__ import annotations
  import pytest
  ```
- **Recommendation:** Move tests into `tests/unit/core/` at repository root and keep package directories source-only.

### Violation 6: Unit tests stored in source package directory (outside required root)

- **File:** `packages/rentl-core/tests/unit/core/test_migrate.py:1`
- **Severity:** High
- **Evidence:**
  ```
  """Unit tests for migration registry and engine."""
  from __future__ import annotations
  import re
  ```
- **Recommendation:** Consolidate these tests under `tests/unit/` so all unit tests are discoverable by the configured test root.

### Violation 7: Integration-style `Given/When/Then` format not used consistently

- **File:** `tests/integration/core/test_deterministic_qa.py:11`
- **Severity:** Medium
- **Evidence:**
  ```
  import pytest
  
  # Apply integration marker
  pytestmark = pytest.mark.integration

  def test_given_lines_with_issues_when_running_qa_then_issues_detected(...)
  ```
- **Recommendation:** Convert this and peers to feature-based `pytest_bdd` flow (`scenarios(...)`, `@given/@when/@then`) to match the tier rule.

### Violation 8: Integration-style `Given/When/Then` format not used consistently

- **File:** `tests/integration/core/test_doctor.py:10`
- **Severity:** Medium
- **Evidence:**
  ```
  import tomllib
  import pytest
  
  # Apply integration marker
  pytestmark = pytest.mark.integration
  ```
- **Recommendation:** Refactor to BDD step functions and bind to a `.feature` scenario file.

### Violation 9: Integration-style `Given/When/Then` format not used consistently

- **File:** `tests/integration/byok/test_openrouter_runtime.py:6`
- **Severity:** Medium
- **Evidence:**
  ```
  from unittest.mock import AsyncMock, MagicMock, patch
  from rentl_llm.openai_runtime import OpenAICompatibleRuntime
  ```
- **Recommendation:** Migrate this test module to BDD format or explicitly document as a lower-level integration exception.

### Violation 10: Integration-style `Given/When/Then` format not used consistently

- **File:** `tests/quality/cli/test_preset_validation.py:18`
- **Severity:** Medium
- **Evidence:**
  ```
  import pytest
  
  @pytest.mark.quality
  @pytest.mark.api
  def test_openrouter_preset_validates_against_live_api(...):
  ```
- **Recommendation:** Prefer BDD `Given/When/Then` form for quality-tier consistency with the standard.

### Violation 11: Quality test timeout exceeds 30-second limit

- **File:** `tests/quality/pipeline/test_golden_script_pipeline.py:37`
- **Severity:** Medium
- **Evidence:**
  ```
  # 90s timeout per scenario — pipeline tests chain multiple sequential LLM calls
  pytestmark = pytest.mark.timeout(90)
  ```
- **Recommendation:** Reduce each scenario to <=30s or split the pipeline into smaller bounded scenarios.

## Compliant Examples

- `tests/quality/pipeline/test_golden_script_pipeline.py:33` — feature-driven binding via `scenarios(...)`.
- `tests/integration/cli/test_doctor.py:20` — BDD `scenarios(...)` with `@given/@when/@then`.
- `tests/integration/byok/test_openai_runtime.py:22` — BDD step-style integration test style.
- `tests/unit/core/test_version.py:1` — unit test located under `tests/unit` with a short isolated scope.

## Scoring Rationale

- **Coverage:** Approximately 92% of test files are located under the three required root tiers. Violations are concentrated in a small set of files (`134` test files found, `11` with direct violations).
- **Severity:** High severity is assigned to files outside required directories because they bypass the repository’s standardized discovery path; medium severity for style/timing exceptions.
- **Trend:** Mixed.
  - Current structure is mostly compliant.
  - Historical artifacts in `tests/features` and `packages/rentl-core/tests/unit` indicate drift from the standard.
- **Risk:** Moderate.
  - Non-root tests can be missed by standard CI invocation.
  - Mixed test style reduces predictability of tier intent.
  - A single quality test currently exceeds the documented 30-second bound.
