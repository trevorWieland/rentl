# Quality Test Suite - Shaping Notes

## Scope

Add a quality test suite using pydantic-evals that validates all five agents
(context, pretranslation, translate, QA, edit) with real LLM calls. Tests
must be BDD-style, run under `tests/quality/`, and remain under 30 seconds
per test. Evaluation must include deterministic checks for schema and tool
call formatting, plus LLM-as-judge rubrics for language correctness and
instruction adherence. The initial thresholds can be lenient, with a future
goal of supporting weaker local models reliably.

## Decisions

- Use pydantic-evals datasets/cases/experiments with explicit evaluators.
- Combine deterministic checks with LLM judges (temperature 0) for quality
  dimensions such as language correctness, tool usage, and instruction
  adherence.
- Instrument tool calls for quality tests to validate tool inputs/outputs.
- Address failures via prompt/profile improvements rather than blaming models.
- Keep initial thresholds lenient while establishing a reliability baseline.

## Context

- **Visuals:** None
- **References:**
  - `tests/integration/agents/test_direct_translator.py`
  - `tests/integration/byok/test_openai_runtime.py`
  - `tests/integration/core/test_deterministic_qa.py`
  - `packages/rentl-agents/src/rentl_agents/runtime.py`
- **Product alignment:** Align with test tier rules (real LLMs, BDD style, <30s)

## Standards Applied

- testing/make-all-gate - Verification required before completion
- testing/three-tier-test-structure - Quality tests in `tests/quality/`
- testing/bdd-for-integration-quality - Given/When/Then structure
- testing/no-mocks-for-quality-tests - Real LLMs only
- testing/test-timing-rules - <30s per quality test
- testing/mandatory-coverage - Behavior-driven coverage
- testing/no-test-skipping - No skipped tests
