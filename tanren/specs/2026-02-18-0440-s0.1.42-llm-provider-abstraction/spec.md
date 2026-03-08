spec_id: s0.1.42
issue: https://github.com/trevorWieland/rentl/issues/129
version: v0.1

# Spec: LLM Provider Abstraction & Agent Wiring

## Problem

LLM provider construction is duplicated across 4 call sites (ProfileAgent runtime, BYOK runtime, benchmark judge, AgentHarness), each manually instantiating OpenAIProvider/OpenRouterProvider with copy-pasted routing logic. OpenRouter model IDs are accepted as plain strings with no format validation. The provider allowlist (`only`) is defined in config but never enforced. Agent tools are passed as raw callables instead of typed `pydantic_ai.Tool` objects. The BYOK runtime doesn't use `output_type`/`output_retries`. Pretranslation alignment only checks for extra IDs, not missing ones.

## Goals

- Centralize all LLM provider/model construction behind a single factory function
- Validate OpenRouter model IDs at the config boundary
- Enforce the provider allowlist when configured
- Add preflight compatibility checks before pipeline start
- Fix agent tool registration to use typed `pydantic_ai.Tool` objects
- Add `output_type`/`output_retries` to BYOK runtime
- Fix pretranslation alignment to check both extra and missing IDs
- Inject HTTP client dependency in benchmark downloader

## Non-Goals

- Changing the underlying pydantic-ai or OpenAI SDK versions
- Adding new provider types beyond OpenRouter and generic OpenAI
- Modifying the pipeline orchestration or phase execution logic
- Refactoring the agent prompt system or template rendering

## Acceptance Criteria

- [ ] LLM provider factory — A single `create_model` factory function constructs the correct provider/model pair (OpenRouter or generic OpenAI) from config. All 4 existing call sites use it exclusively.
- [ ] Model ID validation — OpenRouter model IDs validated via `^[^/]+/.+` regex at the Pydantic config boundary. Invalid IDs rejected at parse time with clear error.
- [ ] Provider allowlist enforcement — When `openrouter_provider.only` is configured, the factory rejects models from providers not on the allowlist.
- [ ] Preflight compatibility check — Before pipeline start, a preflight function validates model/provider compatibility (tool_choice, response_format support) and fails fast with actionable errors.
- [ ] Agent tools as `pydantic_ai.Tool` objects — `AgentFactory.resolve_tools` returns `list[pydantic_ai.Tool]` (not raw callables). `AgentHarness` accepts `list[pydantic_ai.Tool]`.
- [ ] BYOK runtime structured output — BYOK runtime uses `output_type` parameter when `result_schema` is provided. `output_retries` configured on Agent construction.
- [ ] Pretranslation alignment checks both directions — Alignment verification checks both extra IDs and missing IDs, with structured feedback for each.
- [ ] HTTP client injection — Benchmark downloader accepts `httpx.AsyncClient` as a dependency instead of creating it directly.
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No direct provider/model instantiation outside the factory** — All `OpenAIProvider`, `OpenRouterProvider`, `OpenAIChatModel`, `OpenRouterModel` construction must go through a single factory function. No call site may construct these directly.
2. **Model ID validation at the config boundary** — OpenRouter model IDs must be validated (regex `^[^/]+/.+`) when the config is loaded/parsed, not at runtime. Invalid IDs must fail fast with a clear error.
3. **Tools registered as `pydantic_ai.Tool` objects with explicit names** — No raw callables passed to Agent or AgentHarness. Every tool must be wrapped in `pydantic_ai.Tool(function, name=...)` before registration.
4. **No test deletions or modifications to make audits pass** — Existing test behavior must be preserved. New tests required for new factory/validation code.
