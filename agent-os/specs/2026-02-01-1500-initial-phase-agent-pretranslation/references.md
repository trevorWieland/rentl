# References: Initial Phase Agent — Pretranslation (Idiom Labeler)

## Reference Implementations

### Context Phase Agent (Primary Reference)

- **Profile**: `packages/rentl-agents/agents/context/scene_summarizer.toml`
- **Phase Prompt**: `packages/rentl-agents/prompts/phases/context.toml`
- **Utilities**: `packages/rentl-agents/src/rentl_agents/context/scene.py`
- **Wiring**: `packages/rentl-agents/src/rentl_agents/wiring.py`
- **Validation Script**: `scripts/validate_scene_summarizer.py`

### Schema Patterns

- **Output Schema**: `packages/rentl-schemas/src/rentl_schemas/phases.py` (`SceneSummary`)
- **Schema Registry**: `packages/rentl-agents/src/rentl_agents/profiles/loader.py` (`SCHEMA_REGISTRY`)

### Template System

- **Variable Definitions**: `packages/rentl-agents/src/rentl_agents/templates.py`
- **Pretranslation Variables**: `PRETRANSLATION_AGENT_VARIABLES` already defined

### Test Patterns

- **Unit Tests**: `tests/unit/rentl-agents/test_context.py`
- **Integration Tests**: `tests/integration/agents/test_profile_loading.py`
- **BDD Feature**: `tests/integration/features/agents/profile_loading.feature`

## Spec Dependencies

- **Spec 15**: Initial Phase Agent — Context (established TOML agent pattern)
- **Spec 14**: Agent Runtime Scaffold (ProfileAgent, PromptComposer)
