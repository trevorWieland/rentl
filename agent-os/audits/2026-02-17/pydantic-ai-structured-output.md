---
standard: pydantic-ai-structured-output
category: global
score: 76
importance: High
violations_count: 3
date: 2026-02-18
status: violations-found
---

# Standards Audit: Pydantic-AI Structured Output for LLM Calls

**Standard:** `global/pydantic-ai-structured-output`
**Date:** 2026-02-18
**Score:** 76/100
**Importance:** High

## Summary

LLM execution is mostly centralized through `pydantic_ai.Agent`, and most production agent paths use typed output models and provider-aware model settings. However, the BYOK runtime still has non-compliant branches that do not set `output_type` for plain-text prompts and omits `output_retries` where `Agent` is used. The same runtime also does not align with the project-wide retry/validation pattern used by the newer harness/runtime/judge layers.

## Violations

### Violation 1: Unstructured `Agent` calls lack `output_type` in BYOK runtime

- **File:** `packages/rentl-llm/src/rentl_llm/openai_runtime.py:87`
- **Severity:** High
- **Evidence:**
  ```python
  agent = Agent(model, instructions=instructions)
  result = await agent.run(
      request.prompt,
      model_settings=cast(ModelSettings, model_settings),
  )
  ```
- **Recommendation:** Provide an explicit output schema for non-structured calls (e.g., `output_type=TextOutput`) so all prompt executions are validated by `pydantic_ai`.

### Violation 2: BYOK runtime does not use `output_retries` with Agent validation failures

- **File:** `packages/rentl-llm/src/rentl_llm/openai_runtime.py:74`
- **Severity:** Medium
- **Evidence:**
  ```python
  agent = Agent(
      model, output_type=request.result_schema, instructions=instructions
  )
  result = await agent.run(
      request.prompt,
      model_settings=cast(ModelSettings, model_settings),
  )
  ```
- **Recommendation:** Pass `output_retries` (for example `output_retries=5`) whenever using `Agent(..., output_type=...)` so schema validation failures are retried by pydantic-ai before surfacing as hard failures.

### Violation 3: Manual retry loop bypasses `output_retries` in the generic agent harness

- **File:** `packages/rentl-agents/src/rentl_agents/harness.py:193`
- **Severity:** Medium
- **Evidence:**
  ```python
  for attempt in range(self._max_retries + 1):
      try:
          result = await self._execute_agent(user_prompt)
          self.validate_output(result)
          return result
  ```
  ```python
  agent: Agent[None, OutputT_co] = Agent[None, OutputT_co](
      model=model,
      instructions=self._system_prompt,
      output_type=self._output_type,
      tools=self._tools,
  )
  ```
- **Recommendation:** Configure `output_retries` on the `Agent` instance (and keep a narrow transport-level retry policy separately) to keep validation retries at the pydantic-ai boundary.

## Compliant Examples

- `packages/rentl-core/src/rentl_core/benchmark/judge.py:184` — `Agent` is created with explicit `output_type` and `output_retries=5`.
- `packages/rentl-agents/src/rentl_agents/runtime.py:497` — phase-agent execution passes both `output_type` and `output_retries`.

## Scoring Rationale

- **Coverage:** 3 of 4 key LLM-orchestration areas follow the standard fully; `openai_runtime.py` is a notable exception used across the BYOK path.
- **Severity:** High for loss of typed validation on unstructured responses, plus medium for missing `output_retries` in schema-dependent paths.
- **Trend:** Newer internal agent runtime/judge code shows stronger alignment, while the BYOK runtime remains partially legacy.
- **Risk:** Unstructured BYOK calls can produce non-schema outputs without parser-level validation and increase downstream instability during occasional model-format drifts.
