# References: Multi-Model Verification & Compatibility

## Implementation Files

### Provider Infrastructure
- `packages/rentl-llm/src/rentl_llm/provider_factory.py` — Centralized model creation, preflight checks
- `packages/rentl-llm/src/rentl_llm/providers.py` — Provider detection and capabilities
- `packages/rentl-llm/src/rentl_llm/openai_runtime.py` — OpenAI-compatible runtime adapter

### Config Schemas
- `packages/rentl-schemas/src/rentl_schemas/config.py` — ModelEndpointConfig, ModelSettings, OpenRouterProviderRoutingConfig
- `packages/rentl-schemas/src/rentl_schemas/llm.py` — LlmModelSettings, LlmEndpointTarget, LlmRuntimeSettings

### Agent Runtime
- `packages/rentl-agents/src/rentl_agents/runtime.py` — ProfileAgent, ProfileAgentConfig
- `packages/rentl-agents/src/rentl_agents/providers.py` — Tool compatibility checks
- `packages/rentl-agents/src/rentl_agents/wiring.py` — Profile agent factory functions

### Connection Planning
- `packages/rentl-core/src/rentl_core/llm/connection.py` — Connection planning and validation

### Quality Test Harness
- `tests/quality/agents/quality_harness.py` — QualityModelConfig, build_judge_model_and_settings()
- `tests/quality/agents/conftest.py` — Quality fixtures
- `tests/quality/pipeline/test_golden_script_pipeline.py` — Real LLM pipeline tests

## Issues
- #144 — s0.1.49 Multi-Model Verification & Compatibility (this spec)

## Related Specs
- s0.1.12 — BYOK Config & Endpoint Validation
- s0.1.13 — BYOK Runtime Integration
- s0.1.14 — Agent Runtime Scaffold (pydantic-ai)
- s0.1.25 — Quality Test Suite
- s0.1.28 — OpenRouter Full Support
- s0.1.42 — LLM Provider Abstraction & Agent Wiring
