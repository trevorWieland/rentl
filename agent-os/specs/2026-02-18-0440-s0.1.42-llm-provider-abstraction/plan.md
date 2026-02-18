spec_id: s0.1.42
issue: https://github.com/trevorWieland/rentl/issues/129
version: v0.1

# Plan: LLM Provider Abstraction & Agent Wiring

## Decision Record

This work was driven by the 2026-02-17 standards audit which identified 13 violations across 5 standards in the LLM provider and agent wiring code. The core problem is duplicated provider construction logic across 4 call sites, with no validation or enforcement of OpenRouter-specific constraints. The fix centralizes construction behind a factory, adds validation at config boundaries, and fixes several secondary issues (tool registration, structured output, alignment checks).

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on issue branch

- [x] Task 2: Create LLM provider factory with validation
  - New module `packages/rentl-llm/src/rentl_llm/provider_factory.py`
  - `create_model()` function: takes endpoint config + model config, returns `(Model, ModelSettings)` tuple
  - Routes OpenRouter vs generic OpenAI based on `detect_provider()`
  - Model ID validation: regex `^[^/]+/.+` enforced when provider is OpenRouter
  - Provider allowlist: checks `only` field against model ID prefix when configured
  - Unit tests: `packages/rentl-llm/tests/unit/test_provider_factory.py`
    - Test OpenRouter routing path
    - Test generic OpenAI routing path
    - Test model ID validation (valid, invalid formats)
    - Test allowlist enforcement (allowed, blocked, unconfigured)

- [ ] Task 3: Add preflight compatibility check
  - New function in `packages/rentl-llm/src/rentl_llm/provider_factory.py` or separate module
  - Validates tool_choice/response_format compatibility for the configured provider
  - Called from CLI pipeline entry point (`services/rentl-cli/src/rentl/main.py` ~line 915)
  - Fails fast with actionable error messages listing unsupported features
  - Unit tests for preflight pass/fail scenarios

- [ ] Task 4: Migrate all call sites to use factory
  - `packages/rentl-agents/src/rentl_agents/runtime.py:436-464` — ProfileAgent runtime
  - `packages/rentl-llm/src/rentl_llm/openai_runtime.py:53-109` — BYOK runtime
  - `packages/rentl-core/src/rentl_core/benchmark/judge.py:83-104` — Rubric judge
  - `packages/rentl-agents/src/rentl_agents/harness.py:229-240` — AgentHarness
  - Each site replaced with single `create_model()` call
  - Existing tests must continue passing without modification

- [ ] Task 5: Fix agent tool registration
  - `packages/rentl-agents/src/rentl_agents/factory.py:292` — `resolve_tools` returns `list[pydantic_ai.Tool]` with explicit names instead of raw callables
  - `packages/rentl-agents/src/rentl_agents/harness.py:86` — Accept `list[pydantic_ai.Tool]` instead of `list[Callable[..., dict[str, JsonValue]]]`
  - Unit tests verify Tool objects are produced with correct names
  - Acceptance check: no raw callables in tool passing path

- [ ] Task 6: Add output_type/output_retries to BYOK runtime
  - `packages/rentl-llm/src/rentl_llm/openai_runtime.py:74-87` — Always pass `output_type` when `result_schema` provided
  - Add `output_retries` parameter to Agent construction
  - Evaluate manual retry loop in harness (`harness.py:193-208`) — either remove if output_retries handles it, or document why both are needed
  - Unit tests for structured output path with output_retries

- [ ] Task 7: Fix pretranslation alignment
  - `packages/rentl-agents/src/rentl_agents/wiring.py:425-437` — Check both extra and missing IDs
  - Structured feedback message for missing IDs: "Missing: [ids]. Return annotations for all provided line_id values."
  - Unit tests for extra-only, missing-only, and both-direction scenarios
  - Acceptance check: alignment failure on missing IDs triggers retry with feedback

- [ ] Task 8: Inject HTTP client dependency in downloader
  - `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:57` — Accept optional `httpx.AsyncClient` as constructor parameter
  - Default to creating client internally if none provided (backwards compatible)
  - Use injected client when provided (enables testing without network)
  - Update existing tests to use injected client where appropriate
