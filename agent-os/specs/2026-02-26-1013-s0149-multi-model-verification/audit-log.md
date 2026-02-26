# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — `endpoint_type` validation path raises raw `AttributeError` for null/non-string input (`packages/rentl-schemas/src/rentl_schemas/compatibility.py:56-59`) instead of returning a structured `ValidationError`.
- **Task 2** (round 2): FAIL — `object` type annotation remains in `_coerce_endpoint_type`, violating `strict-typing-enforcement` (`packages/rentl-schemas/src/rentl_schemas/compatibility.py:58`).
