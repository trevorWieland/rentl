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
- **Task 5** (round 2): PASS — Registry-driven parametrization is fixed and verified; `pytest --collect-only` now discovers 9 per-model compatibility scenarios with no missing `model_entry` fixture errors.
- **Task 6** (round 1): FAIL — Task 6 fixes are implemented, but the new override wiring (`supports_tool_choice_required`, `max_output_retries`) lacks direct regression coverage in schema, runner, and provider-factory tests.
- **Task 7** (round 1): FAIL — LM Studio lifecycle guarantees break on unload/load-failure paths: pre-load unload errors are warning-only and load failures return before the cleanup `finally` runs.
- **Task 7** (round 2): PASS — Fail-fast unload handling and cleanup-guarded local verification are implemented and verified in `load_lm_studio_model`/`verify_model`, including unload-failure and load-failure cleanup tests.
- **Gate triage** (round 1): test failures — compatibility verification now exceeds quality-tier timing budget for multiple "verified" models (timeouts + context retry exhaustion), and pipeline quality translate run has retry amplification that can consume the full 30s limit before completion.
- **Task 7** (round 3): FAIL — `load_lm_studio_model` still proceeds with `/load` when model listing fails, so Task 7 single-model residency is not guaranteed (`packages/rentl-core/src/rentl_core/compatibility/loader.py:149-158`, `tests/unit/core/compatibility/test_loader.py:217-242`).
- **Gate triage** (round 2): test failures — LM Studio local-model list endpoint contract drift (`GET /api/v1/models/list` returns 404) and quality request budgets still exceed the 30s cap in pretranslation + compatibility failure paths.
