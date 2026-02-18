---
standard: no-mocks-for-quality-tests
category: testing
score: 100
importance: High
violations_count: 0
date: 2026-02-17
status: clean
---

# Standards Audit: No Mocks for Quality Tests

**Standard:** `testing/no-mocks-for-quality-tests`
**Date:** 2026-02-17
**Score:** 100/100
**Importance:** High

## Summary

The quality suite consistently exercises real LLM-backed behavior, while integration tests intentionally isolate LLM adapters and patch runtime boundaries. There were no files found that use mocks in quality tests or real LLM calls in integration-level flow tests. Coverage appears consistent across the checked quality and integration directories, with clear fixtures enforcing the intended test-layer boundary.

## Violations

No violations found.

## Compliant Examples

- `tests/quality/agents/quality_harness.py:30-57` — quality harness enforces `RENTL_QUALITY_*` configuration and builds real model config instead of test doubles.
  ```python
  def load_quality_model_config() -> QualityModelConfig:
      _load_env_file()
      api_key = _require_env("RENTL_QUALITY_API_KEY")
      base_url = _require_env("RENTL_QUALITY_BASE_URL")
  ```

- `tests/quality/agents/test_translate_agent.py:166-170` — quality dataset uses `LLMJudge(..., model=quality_judge_model)` with real judge model from fixtures.
  ```python
  LLMJudge(
      rubric=language_rubric,
      include_input=True,
      model=quality_judge_model,
  )
  ```

- `tests/quality/pipeline/test_golden_script_pipeline.py:7-9, 121-132` — quality pipeline BDD explicitly requires real quality LLM endpoints via `RENTL_QUALITY_*`.
  ```python
  # These tests verify that ... with real LLM runtime
  if not os.getenv("RENTL_QUALITY_API_KEY"):
      raise ValueError("RENTL_QUALITY_API_KEY must be set for quality tests")
  ```

- `tests/integration/conftest.py:141-151` — integration fixture explicitly replaces `_build_llm_runtime` with `FakeLlmRuntime`.
  ```python
  @pytest.fixture
  def mock_llm_runtime(...):
      monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: fake_llm_runtime)
      yield fake_llm_runtime
  ```

- `tests/integration/cli/test_validate_connection.py:177-181` — integration scenario consumes `mock_llm_runtime` fixture instead of real API execution.
  ```python
  def when_run_validate_connection(ctx: ValidateConnectionContext, cli_runner: CliRunner,
      mock_llm_runtime: FakeLlmRuntime,
  ) -> None:
  ```

- `tests/integration/benchmark/test_judge_flow.py:58-63` — integration judge flow test explicitly mocks `pydantic_ai.Agent.run`.
  ```python
  async def mock_agent_run(...):
      ...
  monkeypatch.setattr("pydantic_ai.Agent.run", mock_agent_run)
  ```

- `tests/integration/benchmark/test_cli_command.py:325-327` — integration benchmark CLI patches `RubricJudge` for deterministic mocked flow.
  ```python
  with (
      patch("rentl.main.RubricJudge", return_value=mock_judge),
      patch("rentl.main.Progress.update", side_effect=track_progress_update),
  ):
  ```

- `tests/integration/byok/test_openrouter_runtime.py:50-57` — BYOK integration tests mock provider/model classes to validate routing without external calls.
  ```python
  with patch("rentl_llm.openai_runtime.OpenRouterProvider") as mock_provider,
       patch("rentl_llm.openai_runtime.OpenRouterModel") as mock_model,
       patch("rentl_llm.openai_runtime.Agent") as mock_agent,
  ```

## Scoring Rationale

- **Coverage:** 100% of relevant quality and integration test paths reviewed enforce the expected layer: quality uses real model configuration/judges, and integration patches/fakes LLM adapters.
- **Severity:** No violations found, so no risk from mocking-at-wrong-layer behavior.
- **Trend:** Recent and older quality files (`tests/quality/cli/test_preset_validation.py`, `tests/quality/pipeline/test_golden_script_pipeline.py`) and integration fixtures (`tests/integration/conftest.py`) consistently apply the same principle.
- **Risk:** Practical risk is low; the standard is well implemented for the tested codepaths.
