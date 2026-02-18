# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — Runtime-only model ID validation (not config-boundary) plus strict-typing and mock-verification standard violations in new factory/tests.
- **Task 2** (round 2): PASS — Config-boundary OpenRouter model ID validation added in `RunConfig`, strict typing restored in factory/tests, and execution-boundary mocks are asserted as invoked/not invoked.
- **Task 3** (round 1): FAIL — Preflight uses static capability detection instead of a real probe request, and CLI endpoint deduping can skip validation for distinct routing configs.
- **Task 3** (round 2): PASS — Preflight now performs a real probe request before execution and CLI preflight dedup includes endpoint refs so distinct endpoint configurations are validated.
- **Task 4** (round 1): PASS — All four targeted call sites now construct models via `create_model()` only, with no direct provider/model instantiation outside `provider_factory.py`; updated unit suites pass.
- **Task 5** (round 1): PASS — AgentFactory now wraps tools as named `pydantic_ai.Tool` objects, AgentHarness accepts `list[Tool]`, and updated unit tests validate name-preserving tool registration.
- **Task 6** (round 1): FAIL — BYOK/runtime output_retries wiring is implemented and tested, but Task 6's required "remove or document" decision for harness retry layering is not documented in code, and new dead fallback logic was introduced in `_execute_agent`.
- **Task 6** (round 2): PASS — BYOK structured output now passes `output_type` plus `output_retries`, harness passes configurable `output_retries`, and retry-layer rationale is documented in code with all targeted unit tests passing.
- **Task 7** (round 1): PASS — Pretranslation alignment now validates both extra and missing IDs via shared alignment feedback, and targeted retry tests for extra-only, missing-only, both-direction mismatch, and retry exhaustion all pass.
