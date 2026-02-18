---
standard: batch-alignment-feedback
category: global
score: 74
importance: High
violations_count: 1
date: 2026-02-17
status: violations-found
---

# Standards Audit: Batch Alignment Feedback

**Standard:** `global/batch-alignment-feedback`
**Date:** 2026-02-17
**Score:** 74/100
**Importance:** High

## Summary
The codebase partially applies batch alignment checks, with a centralized helper and two phase agents enforcing full ID reconciliation on retries. However, the pretranslation batch path does not validate full output/input alignment and therefore does not satisfy the standard’s minimum required behavior. This creates the main compliance gap and leaves one high-impact area with silent ID drift risk during retries.

## Violations

### Violation 1: Pretranslation alignment validation is not complete for batch output contracts

- **File:** `packages/rentl-agents/src/rentl_agents/wiring.py:395`
- **Severity:** High
- **Evidence:**
  ```python
  expected_ids = [line.line_id for line in chunk]
  expected_set = set(expected_ids)
  ...
  actual_ids = [idiom.line_id for idiom in result.idioms]
  extra_ids = [
      line_id for line_id in actual_ids if line_id not in expected_set
  ]
  if extra_ids:
      alignment_feedback = (
          "Alignment error: idiom line_id values must come from the "
          "input lines only. "
          f"Extra: {_format_id_list(extra_ids)}. "
          "Return idioms using only the provided line_id values."
      )
  ```
- **Recommendation:** Replace this with structured full alignment feedback consistent with the standard, including explicit missing/extra checks and retry-safe messaging. If the intent is strict 1:1 alignment for the phase output, use `_alignment_feedback(...)` directly and require exact counts. If pretranslation remains sparse-by-design, document that contract explicitly and implement phase-specific feedback that still reports all discrepancies deterministically before retry.

## Compliant Examples

- `packages/rentl-agents/src/rentl_agents/wiring.py:107` — centralized `_alignment_feedback` computes missing, extra, and duplicate discrepancies and appends the required retry instruction.
- `packages/rentl-agents/src/rentl_agents/wiring.py:599` — translate phase applies `_alignment_feedback` to `expected_ids` vs `actual_ids` and retries before surfacing an error.
- `packages/rentl-agents/src/rentl_agents/wiring.py:779` — QA phase applies the same structured alignment routine for output IDs before accepting batch results.
- `packages/rentl-agents/src/rentl_agents/wiring.py:942` — edit phase uses explicit per-line ID equality before accepting edited output, enforcing output/input ID correspondence for single-line edit units.

## Scoring Rationale

- **Coverage:** Most batch-alignment-aware agents (translate/qa) apply full missing/extra checks with structured retry feedback, but pretranslation only enforces one of the required discrepancy types, so overall coverage is incomplete.
- **Severity:** One high-severity violation remains because it can let invalid batch outputs pass retries without correction.
- **Trend:** No strong trend signal is visible from the current snapshot; alignment behavior is mixed within the same module, with some agents fully compliant and pretranslation partially aligned.
- **Risk:** Medium-to-high practical impact: pretranslation ID drift can yield incorrect or incomplete idiom annotation coverage without immediate failure, reducing downstream quality and traceability.
