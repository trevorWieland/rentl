---
standard: mock-execution-boundary
category: testing
score: 44
importance: High
violations_count: 5
date: 2026-02-17
status: violations-found
---

# Standards Audit: Mock at the Execution Boundary

**Standard:** `testing/mock-execution-boundary`
**Date:** 2026-02-17
**Score:** 44/100
**Importance:** High

## Summary

Compliance is mixed. The codebase has a strong pattern in `tests/integration/cli/test_init.py` using `ProfileAgent.run` stubs, but several other integration tests still mock earlier pipeline/LLM internals. The most important gap is mocking `rentl.main._build_llm_runtime` and `pydantic_ai` internals in integration tests instead of stubbing at the execution boundary. Missing `mock_call_count` assertions in a couple of tests leaves part of this standard unmet.

## Violations

### Violation 1: Integration tests mock the CLI runtime factory instead of `ProfileAgent.run`

- **File:** `tests/integration/cli/test_run_pipeline.py:146`
- **Severity:** High
- **Evidence:**
  ```python
  monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: FakeLlmRuntime())
  ```
- **Recommendation:** Move the mock boundary to `ProfileAgent.run` and return outputs matching `self._output_type`, then assert the mock was invoked.

### Violation 2: Integration tests mock `cli_main._build_llm_runtime` in run-phase BDD flow

- **File:** `tests/integration/cli/test_run_phase.py:140`
- **Severity:** High
- **Evidence:**
  ```python
  monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: FakeLlmRuntime())
  ```
- **Recommendation:** Replace with `ProfileAgent.run` boundary mocking at the point of execution to align with integration-tier rules.

### Violation 3: Integration judge flow mocks `pydantic_ai.Agent.run`

- **File:** `tests/integration/benchmark/test_judge_flow.py:102`
- **Severity:** High
- **Evidence:**
  ```python
  monkeypatch.setattr("pydantic_ai.Agent.run", mock_agent_run)
  ```
- **Recommendation:** Avoid patching pydantic-ai internals in integration tests; mock at the project’s execution boundary for judge evaluation and validate that the mock path is used.

### Violation 4: Integration BYOK runtime tests patch pydantic-ai `Agent` and never verify it was called

- **File:** `tests/integration/byok/test_openrouter_runtime.py:53`
- **Severity:** High
- **Evidence:**
  ```python
  patch("rentl_llm.openai_runtime.Agent") as mock_agent,
  ...
  mock_agent_instance = MagicMock()
  mock_agent_instance.run = AsyncMock()
  mock_agent.return_value = mock_agent_instance
  ```
- **Recommendation:** For integration tests, avoid patching `rentl_llm.openai_runtime.Agent`; mock closer to `OpenAICompatibleRuntime.run_prompt` boundaries and assert the mock boundary was invoked.

### Violation 5: Integration onboarding test does not verify mocked `ProfileAgent.run` invocation

- **File:** `tests/integration/cli/test_onboarding_e2e.py:152`
- **Severity:** Medium
- **Evidence:**
  ```python
  mock_call_count = {"count": 0}

  async def mock_agent_run(self: ProfileAgent, payload: object) -> object:
      await asyncio.sleep(0)
      mock_call_count["count"] += 1
      ...

  monkeypatch.setattr(ProfileAgent, "run", mock_agent_run)
  ```
- **Recommendation:** Add an assertion after execution (like `assert mock_call_count["count"] > 0`) to satisfy execution-boundary verification.

## Compliant Examples

- `tests/integration/cli/test_init.py:289` — defines `mock_call_count`, patches `ProfileAgent.run`, and asserts invocation at `tests/integration/cli/test_init.py:407`.
- `tests/integration/cli/test_init.py:298` — returns `SceneSummary`, `IdiomAnnotationList`, `TranslationResultList`, etc. based on `self._output_type` for schema-valid boundary-mock behavior.

## Scoring Rationale

- **Coverage:** The integration scope of this audit has approximately 1 clearly fully compliant boundary-mock pattern versus 5 violations, so execution-boundary compliance is low.
- **Severity:** There are 3 High and 2 Medium violations, primarily around mocking too-early internals in integration tests, which can mask real execution-path failures.
- **Trend:** Mixed quality. Recent onboarding-style tests use `ProfileAgent.run`, but older/focused integration suites still target lower-level internals and factories.
- **Risk:** Moderate-to-high. These violations can create false positives: tests may pass while the real execution boundary is bypassed or unverified.
