# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — `endpoint_type` validation path raises raw `AttributeError` for null/non-string input (`packages/rentl-schemas/src/rentl_schemas/compatibility.py:56-59`) instead of returning a structured `ValidationError`.
- **Task 2** (round 2): FAIL — `object` type annotation remains in `_coerce_endpoint_type`, violating `strict-typing-enforcement` (`packages/rentl-schemas/src/rentl_schemas/compatibility.py:58`).
- **Task 1** (round 1): PASS — Spec documentation bundle is complete in commit `1ea0875` (`spec.md`, `plan.md`, `demo.md`, `standards.md`, `references.md`) and matches the Task 1 deliverables.
- **Task 3** (round 1): FAIL — `verify_model` drops valid zero-valued overrides via truthy fallback logic, and Task 3 tests still use forbidden `object` type annotations.
- **Task 2** (round 3): PASS — Task 2 schema/registry implementation is compliant; resolved signposts were verified in code and `tests/unit/schemas/test_compatibility.py` passes (21/21).
- **Task 4** (round 1): FAIL — `verify-models` does not handle unexpected verifier exceptions at the CLI boundary and is missing output-formatting coverage promised by Task 4 tests.
- **Task 4** (round 2): PASS — CLI runtime exception handling and output-formatting coverage are implemented and verified; `tests/unit/cli/test_verify_models.py` passes (12/12).
- **Task 5** (round 1): FAIL — Compatibility quality test is not registry-parameterized in practice; pytest collects one scenario and fails with `fixture 'model_entry' not found`.
