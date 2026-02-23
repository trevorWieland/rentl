# References: s0.1.26 — Declarative Agent Config

## Implementation Files

### Core Schemas
- `packages/rentl-schemas/src/rentl_schemas/agents.py` — AgentProfileConfig, AgentProfileMeta, AgentRequirements, AgentOrchestration, AgentPromptConfig, ToolAccessConfig, ModelHints
- `packages/rentl-schemas/src/rentl_schemas/config.py` — PipelineConfig, phase config schemas

### Agent Loading & Runtime
- `packages/rentl-agents/src/rentl_agents/profiles/loader.py` — Profile discovery, loading, validation, schema registry
- `packages/rentl-agents/src/rentl_agents/runtime.py` — ProfileAgent runtime, ProfileAgentConfig
- `packages/rentl-agents/src/rentl_agents/wiring.py` — Phase-specific agent factory functions
- `packages/rentl-agents/src/rentl_agents/templates.py` — Template variable system, allowed vars per phase

### Agent Definitions (TOML Profiles)
- `packages/rentl-agents/agents/context/` — Context phase agents
- `packages/rentl-agents/agents/pretranslation/` — Pretranslation phase agents
- `packages/rentl-agents/agents/translate/` — Translation phase agents
- `packages/rentl-agents/agents/qa/` — QA phase agents
- `packages/rentl-agents/agents/edit/` — Edit phase agents

### Prompt Layers
- `packages/rentl-agents/prompts/root.toml` — Root prompt layer
- `packages/rentl-agents/prompts/phases/` — Phase-specific prompt layers

### Pipeline Configuration
- `rentl.toml` — Top-level pipeline config

## Related Issues
- #15 s0.1.14 Agent Runtime Scaffold (pydantic-ai) — dependency (CLOSED)
- #16 s0.1.15 Initial Phase Agent: Context — dependency (CLOSED)
- #17 s0.1.16 Initial Phase Agent: Pretranslation — dependency (CLOSED)

## Related Specs
- `agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/` — Related provider config work
