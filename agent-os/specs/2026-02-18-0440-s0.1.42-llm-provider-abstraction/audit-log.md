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
- **Task 8** (round 1): PASS — (inferred from integration test suite passing)
- **Demo** (run 1): FAIL — Steps 1-3 pass; step 4 fails with `_resolve_reasoning_effort` crash on plain string from Pydantic `use_enum_values=True`. Task 9 added. (3 run pass, 1 run fail, 3 not executed)
- **Task 9** (round 1): FAIL — Core fix is present and targeted tests pass, but Task 9 introduces unused `# type: ignore[arg-type]` suppressions flagged by `ty` at `tests/unit/llm/test_provider_factory.py:93` and `tests/unit/llm/test_provider_factory.py:195`.
- **Demo** (run 2): FAIL — Steps 1-4, 6-7 pass; step 5 fails due to local model server unavailable at localhost:5000 (environment issue, not code defect). Factory routing to OpenAIChatModel confirmed correct. (6 run pass, 1 run fail)
- **Demo** (run 3): FAIL — Steps 1-3, 6-7 pass; step 4 fails due to OpenRouter `require_parameters=true` rejecting all models (external service change, not code defect — same code passed run 2); step 5 fails due to local model server still unavailable. Factory code verified correct with `require_parameters=false`. (5 run pass, 2 run fail)
- **Demo** (run 4): FAIL — Steps 1-3, 6-7 pass; step 4 confirmed factory works end-to-end with `require_parameters=false` (Agent returned "Hello"), but `require_parameters=true` still 404 at OpenRouter (signpost #3); step 5 local model server still unavailable (signpost #2). Both are environment/external issues, not code defects. No new tasks added. (5 run pass, 2 run fail)
- **Demo** (run 5): FAIL — Steps 1-3, 6-7 pass; step 4 raw HTTP to OpenRouter succeeds but pydantic-ai Agent 404 due to unsupported parameters (signpost #3); step 5 local model server still unavailable (signpost #2). Both environment/external issues, no code defects, no new tasks. (5 run pass, 2 run fail)
- **Demo** (run 6): FAIL — Steps 1-3, 6-7 pass; step 4 factory call with require_parameters=False succeeds but True still 404 at OpenRouter (signpost #3); step 5 local model server still unavailable (signpost #2). Both environment/external issues, no code defects, no new tasks. (5 run pass, 2 run fail)
- **Demo** (run 7): FAIL — Steps 1-3, 6-7 pass; step 4 raw HTTP succeeds but pydantic-ai Agent 404 due to OpenRouter require_parameters interaction (signpost #3); step 5 local model server still unavailable (signpost #2). Both environment/external issues, no code defects, no new tasks. (5 run pass, 2 run fail)
- **Demo** (run 8): FAIL — Steps 1-3, 6-7 pass; step 4 factory works with require_parameters=False (Agent returned "Hello") but True still 404 at OpenRouter (signpost #3); step 5 local model server still unavailable (signpost #2). Both environment/external issues, no code defects, no new tasks. (5 run pass, 2 run fail)
- **Demo** (run 9): FAIL — Steps 1-3, 6-7 pass; step 4 factory works with require_parameters=False (Agent returned "Hello") but True still 404 at OpenRouter (signpost #3); step 5 local model server still unavailable (signpost #2). Both environment/external issues, no code defects, no new tasks. (5 run pass, 2 run fail)
- **Demo** (run 10): FAIL — Steps 1-4, 6-7 pass (step 4 now passes: OpenRouter require_parameters=True works for qwen/qwen3-30b-a3b); step 5 local model server still unavailable at localhost:5000 (signpost #2). Environment issue only, no code defects, no new tasks. (6 run pass, 1 run fail)
