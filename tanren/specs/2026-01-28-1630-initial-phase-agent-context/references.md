# References for Initial Phase Agent: Context

## Similar Implementations

### 1. Agent Runtime Scaffold (Spec 14)

- **Location:** `packages/rentl-agents/src/rentl_agents/harness.py`
- **Relevance:** Provides base AgentHarness class with pydantic-ai integration
- **Key patterns:**
  - `AgentHarness[InputT, OutputT]` generic class with typed input/output
  - Prompt template rendering via `PromptRenderer`
  - Tool registration with pydantic-ai `Agent`
  - Retry logic with exponential backoff
  - Input/output validation via Pydantic

### 2. Agent Factory

- **Location:** `packages/rentl-agents/src/rentl_agents/factory.py`
- **Relevance:** Shows pattern for creating agent instances from configuration
- **Key patterns:**
  - `AgentConfig` schema for agent configuration
  - `AgentFactory.create_agent()` instantiation method
  - Tool registry integration
  - Agent instance caching

### 3. Phase Schemas

- **Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Relevance:** Defines input/output schemas for all phases
- **Key patterns:**
  - `ContextPhaseInput`: run_id, source_lines, project_context, style_guide, glossary
  - `ContextPhaseOutput`: run_id, phase, scene_summaries, context_notes, glossary
  - `SceneSummary`: scene_id, summary, characters

### 4. Orchestrator Context Phase

- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py` (lines 540-630)
- **Relevance:** Shows how context phase is executed in pipeline
- **Key patterns:**
  - Work chunking via `_build_work_chunks()`
  - Agent pool execution via `_run_agent_pool()`
  - Output merging via `_merge_context_outputs()`
  - Progress tracking per scene

### 5. Tool System

- **Location:** `packages/rentl-agents/src/rentl_agents/tools.py`
- **Relevance:** Existing tool protocol and implementations
- **Key patterns:**
  - `AgentToolProtocol` with name, description, execute, schema
  - `AgentTool` base class
  - Tool-specific input/output schemas
  - Error handling in tool execution

### 6. Prompt Renderer

- **Location:** `packages/rentl-agents/src/rentl_agents/prompts.py`
- **Relevance:** Template rendering for prompts
- **Key patterns:**
  - Variable substitution with `{{variable}}` syntax
  - Template caching
  - Type conversion

### 7. Run Configuration

- **Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`
- **Relevance:** Shows configuration schema patterns
- **Key patterns:**
  - Nested Pydantic schemas with validators
  - `model_validator(mode="after")` for cross-field validation
  - Optional fields with defaults
  - Reference resolution (endpoint_ref)

## External References

### pydantic-ai Documentation
- **URL:** https://ai.pydantic.dev/
- **Relevance:** Agent framework patterns, structured output, tool registration

### TOML Configuration Pattern
- **Tech Stack:** TOML for configuration (from tech-stack.md)
- **Python Library:** tomllib (stdlib) or toml package
