---
standard: no-placeholder-artifacts
category: global
score: 91
importance: Medium
violations_count: 2
date: 2026-02-18
status: clean
---

# Standards Audit: No Placeholder Artifacts

**Standard:** `global/no-placeholder-artifacts`
**Date:** 2026-02-18
**Score:** 91/100
**Importance:** Medium

## Summary

The codebase is largely compliant: no empty SHA-256 sentinel values (`e3b0...`) or skip-marked tests were found in active implementation and test code. Hashes and computed artifact/ranking values are derived from real content. Two remaining issues are configuration-time/placeholder design concerns: one hardcoded placeholder artifact path and one obsolete placeholder-marked test stub.

## Violations

### Violation 1: Hardcoded placeholder artifact path in production write flow

- **File:** `packages/rentl-core/src/rentl_core/orchestrator.py:1488`
- **Severity:** Medium
- **Evidence:**
  ```python
  def _placeholder_reference(format: ArtifactFormat) -> StorageReference:
      return StorageReference(
          backend=None,
          path=f"placeholder.{format.value}",
          uri=None,
      )
  ```
  The placeholder path is passed directly into artifact persistence (`location=_placeholder_reference(...)`) before write.
- **Recommendation:** Build artifact location from concrete run/artifact identity (e.g., run id + artifact id) before calling the store, and avoid shipping a hardcoded `placeholder.*` path that can become externally visible.
  ```python
  # Example intent
  path = f"run-{run.run_id}/artifact-{artifact_id}.{format.value}"
  location=StorageReference(backend=StorageBackend.FILESYSTEM, path=path, uri=None)
  ```

### Violation 2: Incomplete placeholder-marked benchmark config test

- **File:** `tests/unit/benchmark/test_config.py:129`
- **Severity:** Low
- **Evidence:**
  ```python
  def test_benchmark_config_scoring_mode_validation() -> None:
      """Test BenchmarkConfig scoring_mode validates against literal values."""
      # TODO: Removed in Task 2 - benchmark is head-to-head only now
      # This test is no longer relevant since scoring_mode was removed
      pass
  ```
  The test is retained as a TODO placeholder with no assertions, reducing auditability.
- **Recommendation:** Remove this dead test or replace it with an assertion against the current supported API (or explicitly mark it as deleted in the test suite).

## Compliant Examples

- `packages/rentl-core/src/rentl_core/benchmark/report.py:158` — derives `overall_ranking` from computed Elo ratings instead of accepting a caller-supplied placeholder order.
- `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:105` — computes SHA-256 from actual file contents before comparisons.
- `tests/quality/benchmark/test_benchmark_quality.py:237` — asserts Elo/ranking behavior at runtime rather than hardcoding ranking expectations.

## Scoring Rationale

- **Coverage:** High. Most components that handle sensitive or derived values (hashing, ranking, benchmark report formatting) derive values from real data and are tested.
- **Severity:** Only one medium and one low issue; no critical/high violations in active implementation files.
- **Trend:** Current production code appears better aligned than historical task/spec narratives; remaining findings are isolated and mostly cleanup-oriented.
- **Risk:** Medium. The hardcoded placeholder path is a correctness/integrity risk if storage behavior changes; the test TODO is a maintainability burden with low runtime impact.
