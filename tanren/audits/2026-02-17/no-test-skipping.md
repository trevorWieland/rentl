---
standard: no-test-skipping
category: testing
score: 100
importance: High
violations_count: 0
date: 2026-02-17
status: clean
---

# Standards Audit: No Test Skipping

**Standard:** `testing/no-test-skipping`
**Date:** 2026-02-17
**Score:** 100/100
**Importance:** High

## Summary

Reviewed the Python test code paths and test-run configuration and found no active test skipping in this codebase branch. Targeted searches found no `@pytest.mark.skip`, `@pytest.mark.skipif`, `pytest.mark.skipif`, `pytest.skip()`, or `@pytest.mark.xfail` usages in `tests/**/*.py` or `packages/rentl-core/tests/**/*.py`. The project runs tiered test commands without any skip flags, and environment/feature gating is handled via explicit failing behavior rather than skip decorators.

## Violations

No violations found.

## Compliant Examples

- `tests/quality/cli/test_preset_validation.py:55` — On missing required quality API credentials, the test raises a `ValueError` instead of skipping, which converts a missing precondition into an explicit test failure.
- `Makefile:69-79` — Unit, integration, and quality tier commands run full suite paths (`tests/unit`, `tests/integration`, `tests/quality`) directly, with no pytest skip flags or skip conditions.

## Scoring Rationale

- **Coverage:** 100% of reviewed test files matched this standard (no skip/xfail constructs found in targeted test files).
- **Severity:** No high/critical issues identified because no violations were observed.
- **Trend:** Current test code and runner entries are consistent with fail-fast behavior; there are no mixed patterns of skipped and non-skipped equivalent tests in scanned files.
- **Risk:** Low practical risk for this standard at this point; test bypasses are not being used to hide failures.
