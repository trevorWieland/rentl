# Demo: Standards Review — Declarative Agent Config

rentl now has a formal standard for its declarative agent configuration system. The standard documents how agent profiles are structured in TOML, how prompts are layered, how tools are registered, and how the pipeline orchestrates agents — all grounded in the actual Pydantic schemas and code that enforce these patterns.

In this demo, we prove the standard accurately describes the real config patterns, and that all existing agent profiles comply.

## Environment

- API keys: None needed
- External services: None needed
- Setup: None beyond what `make` provides

## Steps

1. **[RUN]** Verify the standard document exists and covers all required sections — expected: `agent-os/standards/architecture/declarative-agent-config.md` exists with sections for profile schema, TOML structure, prompt layering, template variables, tool registration, model hints, orchestration, and pipeline config

2. **[RUN]** Verify the standards index includes the new entry — expected: `index.yml` contains `declarative-agent-config` under `architecture`

3. **[RUN]** Cross-reference standard against Pydantic schemas — expected: every field in `AgentProfileConfig` and its sub-models is documented in the standard with matching field names and types

4. **[RUN]** Load all agent TOML profiles and validate against schemas — expected: `discover_agent_profiles()` loads all profiles without errors, confirming compliance

5. **[RUN]** Run full verification gate (`make all`) — expected: all tests pass with zero failures

## Results

### Run 1 — s0.1.26 declarative agent config standard (2026-02-22 23:31)
- Step 1 [RUN]: PASS — Standard document exists at `agent-os/standards/architecture/declarative-agent-config.md` with all 8 required sections (Agent Profile Schema, TOML File Structure, Layered Prompt System, Template Variable Registry, Tool Registration & Access Control, Model Hints, Orchestration Config, Pipeline Phase Config)
- Step 2 [RUN]: PASS — `index.yml` contains `declarative-agent-config` under `architecture` with correct description
- Step 3 [RUN]: PASS — All fields in `AgentProfileConfig`, `AgentProfileMeta`, `AgentRequirements`, `AgentOrchestration`, `AgentPromptConfig`, `ToolAccessConfig`, `ModelHints`, `PhasePromptConfig`, `RootPromptConfig`, and `PhaseConfig` are documented with matching field names, types, and constraints
- Step 4 [RUN]: PASS — `discover_agent_profiles()` loaded all 5 profiles (scene_summarizer, idiom_labeler, direct_translator, style_guide_critic, basic_editor) without errors
- Step 5 [RUN]: PASS — `make all` passed: 1040 unit, 95 integration, 9 quality tests all green
- **Overall: PASS**
