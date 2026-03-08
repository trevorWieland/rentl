# References: LLM Provider Abstraction & Agent Wiring

## Issue

- https://github.com/trevorWieland/rentl/issues/129

## Implementation Files

### Provider construction (violations #1-7)

- `packages/rentl-schemas/src/rentl_schemas/llm.py` — LlmModelSettings, LlmEndpointTarget
- `packages/rentl-schemas/src/rentl_schemas/config.py` — OpenRouterProviderRoutingConfig (allowlist `only` field)
- `packages/rentl-llm/src/rentl_llm/openai_runtime.py` — BYOK runtime provider construction
- `packages/rentl-agents/src/rentl_agents/runtime.py` — ProfileAgent runtime provider construction
- `packages/rentl-agents/src/rentl_agents/harness.py` — AgentHarness provider construction
- `packages/rentl-core/src/rentl_core/benchmark/judge.py` — Rubric judge provider construction
- `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py` — Direct httpx.AsyncClient usage

### Agent tool registration (violations #8-9)

- `packages/rentl-agents/src/rentl_agents/factory.py` — AgentFactory.resolve_tools
- `packages/rentl-agents/src/rentl_agents/harness.py` — AgentHarness tool parameter

### Structured output (violations #10-12)

- `packages/rentl-llm/src/rentl_llm/openai_runtime.py` — BYOK runtime Agent construction

### Alignment (violation #13)

- `packages/rentl-agents/src/rentl_agents/wiring.py` — Pretranslation alignment check

### Pipeline entry point

- `services/rentl-cli/src/rentl/main.py` — Pipeline start (preflight check location)

## Audit Reports

- `agent-os/audits/2026-02-17/openrouter-provider-routing.md`
- `agent-os/audits/2026-02-17/adapter-interface-protocol.md`
- `agent-os/audits/2026-02-17/agent-tool-registration.md`
- `agent-os/audits/2026-02-17/pydantic-ai-structured-output.md`
- `agent-os/audits/2026-02-17/batch-alignment-feedback.md`

## Dependencies

- s0.1.12 (#13) — BYOK Config & Endpoint Validation (CLOSED)
- s0.1.13 (#14) — BYOK Runtime Integration (CLOSED)
- s0.1.14 (#15) — Agent Runtime Scaffold (CLOSED)
- s0.1.28 (#112) — OpenRouter Full Support (CLOSED)
