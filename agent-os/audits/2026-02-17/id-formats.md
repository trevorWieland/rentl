---
standard: id-formats
category: architecture
score: 87
importance: High
violations_count: 2
date: 2026-02-17
status: violations-found
---

# Standards Audit: ID Formats

**Standard:** `architecture/id-formats`
**Date:** 2026-02-17
**Score:** 87/100
**Importance:** High

## Summary

The codebase generally enforces the intended ID model: shared primitives define UUIDv7 for internal IDs and human-readable `{word}_{number}` IDs for line/scene/route identifiers, and several production paths generate IDs with `uuid7()`. However, there are two real gaps: one schema field accepts a free-form string where a human-readable line id is expected, and one runtime validator accepts any UUID for run IDs rather than enforcing UUIDv7. Because these are architecture-level integrity checks, overall compliance is good but not complete.

## Violations

### Violation 1: Benchmark result line identifier is not typed as a human-readable ID

- **File:** `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`
- **Severity:** Medium
- **Evidence:**
  ```python
  class HeadToHeadResult(BaseModel):
      """Result of a head-to-head comparison between two translations."""

      line_id: str = Field(description="Unique identifier for the evaluated line")
  ```
- **Recommendation:** Use `LineId` (or a narrowly scoped compatible type) instead of `str` to enforce `{word}_{number}` pattern consistency across line identifiers.
  ```python
  from .primitives import LineId

  line_id: LineId = Field(description="Unique identifier for the evaluated line")
  ```

### Violation 2: Runtime run_id extraction accepts any UUID version

- **File:** `packages/rentl-agents/src/rentl_agents/runtime.py:594`
- **Severity:** Medium
- **Evidence:**
  ```python
  def _extract_run_id(payload: BaseSchema) -> RunId:
      value = getattr(payload, "run_id", None)
      if value is None:
          raise ValueError("payload is missing run_id")
      if not isinstance(value, UUID):
          raise ValueError("run_id must be a UUID")
      return value
  ```
- **Recommendation:** Enforce UUID version 7 in this boundary and fail fast for non-v7 IDs.
  ```python
  if not isinstance(value, UUID):
      raise ValueError("run_id must be a UUID")
  if value.version != 7:
      raise ValueError("run_id must be UUIDv7")
  return value
  ```

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/primitives.py:39` — `Uuid7` is defined with an `AfterValidator` that enforces `value.version == 7`.
- `packages/rentl-schemas/src/rentl_schemas/primitives.py:40` — `HumanReadableId` enforces `^[a-z]+(?:_[0-9]+)+$`.
- `packages/rentl-core/src/rentl_core/orchestrator.py:1349` — artifact creation uses `artifact_id=uuid7()`.
- `packages/rentl-core/src/rentl_core/qa/runner.py:88` — QA issues use `issue_id=uuid7()`, matching UUIDv7 rule for internal IDs.
- `packages/rentl-schemas/src/rentl_schemas/io.py:56` and `packages/rentl-schemas/src/rentl_schemas/io.py:72` — line identifiers are typed as `LineId`.

## Scoring Rationale

- **Coverage:** Most schema and generation points follow the standard; the two identified gaps are concentrated in one benchmark model and one runtime validator.
- **Severity:** Both findings are medium-level integrity issues: they weaken validation guarantees but do not show immediate hard failures in all code paths.
- **Trend:** The core schema and producer-side ID logic are consistently compliant; gaps appear in a specialized comparison model and an input-validation boundary, suggesting isolated drift rather than broad architectural drift.
- **Risk:** The practical risk is moderate: non-conforming IDs can leak into persisted/telemetry-relevant data and reduce reliability of downstream validation, but not yet a widespread systemic failure.
