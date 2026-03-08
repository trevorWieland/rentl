# References for Agent Runtime Scaffold (pydantic-ai)

## Similar Implementations

### OpenAI Runtime (pydantic-ai)

**Location:** `packages/rentl-llm/src/rentl_llm/openai_runtime.py`

**Relevance:** Already implements pydantic-ai integration with OpenAI-compatible endpoints. Provides a working example of using `pydantic_ai.Agent` with custom model providers and settings.

**Key patterns to borrow:**
- Uses `pydantic_ai.Agent` constructor with `model` and `instructions`
- Integrates with `OpenAIProvider` for BYOK endpoints via `base_url` and `api_key`
- Uses `OpenAIChatModel` with model-specific settings (temperature, top_p, presence_penalty, frequency_penalty)
- Supports OpenAI-specific features like `reasoning_effort` and `max_output_tokens`
- Implements `LlmRuntimeProtocol.run_prompt()` method with async execution
- Returns structured `LlmPromptResponse` with `model_id` and `output_text`
- Error handling through pydantic-ai's built-in mechanisms

**Adaptation for agent runtime:**
- Reuse `OpenAICompatibleRuntime` as the LLM backend for agents
- Leverage `Agent` constructor pattern for creating agents
- Apply similar model settings handling for agent configuration
- Use async execution pattern for agent runs

---

### Phase Agent Protocols

**Location:** `packages/rentl-core/src/rentl_core/ports/orchestrator.py`

**Relevance:** Defines the protocol contracts that agent harness must implement. Shows type-safe generic protocol pattern for phase-specific agents.

**Key patterns to borrow:**
- `PhaseAgentProtocol[InputT, OutputT]` generic protocol with `run(payload: InputT) -> OutputT` method
- `PhaseAgentPoolProtocol[InputT, OutputT]` with `run_batch(payloads: list[InputT]) -> list[OutputT]` method
- Phase-specific type aliases: `ContextAgentProtocol`, `PretranslationAgentProtocol`, `TranslateAgentProtocol`, `QaAgentProtocol`, `EditAgentProtocol`
- Pool-specific type aliases: `ContextAgentPoolProtocol`, `TranslateAgentPoolProtocol`, etc.
- Uses `@runtime_checkable` decorator for protocol runtime checking
- Type variables `InputT = TypeVar("InputT", bound=BaseSchema)` and `OutputT = TypeVar("OutputT", bound=BaseSchema)`

**Adaptation for agent runtime:**
- `AgentHarness` must implement `PhaseAgentProtocol[InputT, OutputT]`
- Agent wraps must return correct phase-specific output types
- Support both single agent and agent pool patterns
- Use generic type parameters for input/output schemas

---

### PhaseAgentPool Implementation

**Location:** `packages/rentl-core/src/rentl_core/orchestrator.py` (lines 119-193)

**Relevance:** Shows how agent pools are instantiated, configured, and used in the orchestrator. Provides the integration point for our agent factory.

**Key patterns to borrow:**
- `PhaseAgentPool` class with `agents: list[PhaseAgentProtocol[InputT, OutputT]]` parameter
- `max_parallel: int | None` for concurrency control
- `from_factory()` class method: takes a factory callable and count to create multiple agent instances
- `run_batch()` method executes payloads concurrently while preserving output order
- Uses `asyncio.Semaphore` for concurrency limiting
- Uses `asyncio.TaskGroup` for modern structured concurrency
- Agent selection via round-robin: `agent = self._agents[index % len(self._agents)]`

**Adaptation for agent runtime:**
- `AgentFactory.from_factory()` creates pools of `AgentHarness` instances
- `AgentHarness` wraps must be compatible with `PhaseAgentPool` pattern
- Support `max_parallel` configuration in agent factory
- Preserve output ordering for batch execution

---

### Orchestrator Agent Pool Usage

**Location:** `packages/rentl-core/src/rentl_core/orchestrator.py` (lines 540-630, 632-699, 701-775, 777-847, 849-919)

**Relevance:** Shows how agent pools are passed to orchestrator and used in phase execution. Demonstrates the full integration flow.

**Key patterns to borrow:**
- `PipelineOrchestrator.__init__()` accepts phase agent pools: `context_agents`, `pretranslation_agents`, `translate_agents`, `qa_agents`, `edit_agents`
- Phase execution methods (e.g., `_run_context()`, `_run_translate()`) check if agent pool is configured
- Work chunking: `_build_work_chunks()` splits source lines by strategy (full/scene/route)
- Agent execution via `_run_agent_pool()` helper with `on_batch` callback for progress updates
- Progress metrics: lines processed, scenes summarized, lines translated, etc.
- Merging outputs from multiple agent executions: `_merge_context_outputs()`, `_merge_translate_outputs()`, etc.

**Adaptation for agent runtime:**
- Agent factory must create pools compatible with orchestrator's expectations
- `AgentHarness` instances must work with work chunking and batch execution
- Support progress callbacks in agent execution
- Output merging must handle agent harness outputs correctly

---

### Phase Input/Output Schemas

**Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`

**Relevance:** Defines the input and output schemas for each phase. Agents must consume these inputs and produce these outputs.

**Key patterns to borrow:**
- `ContextPhaseInput`: `run_id`, `source_lines`, `project_context`, `style_guide`, `glossary`
- `ContextPhaseOutput`: `run_id`, `phase`, `project_context`, `style_guide`, `glossary`, `scene_summaries`, `context_notes`
- `TranslatePhaseInput`: `run_id`, `source_lines`, `target_language`, `context`, `glossary`, `style_guide`
- `TranslatePhaseOutput`: `run_id`, `phase`, `target_language`, `translated_lines`
- All schemas use `Field(..., description="...")` with clear descriptions
- Nested schemas: `SceneSummary`, `GlossaryTerm`, `PretranslationAnnotation`, etc.

**Adaptation for agent runtime:**
- `AgentHarness[InputT, OutputT]` must work with these phase schemas
- Prompt templates must inject phase-specific context (project_context, style_guide, glossary)
- Agent outputs must validate against phase output schemas
- Tool lookup must work with phase-specific data structures

---

### BYOK Configuration

**Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`

**Relevance:** Shows how model endpoints and runtime settings are configured. Agents need to access these settings.

**Key patterns to borrow:**
- `LlmEndpoint` schema: `endpoint_id`, `name`, `base_url`, `api_key_env_var`, `timeout_s`
- `LlmModel` schema: `model_id`, `endpoint_ref`, `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`, `reasoning_effort`, `max_output_tokens`
- `LlmRuntime` schema: combines `model` and `endpoint` references
- Phase execution config: `max_parallel_agents` for concurrency control
- Endpoint resolution logic with precedence: agent → phase → default

**Adaptation for agent runtime:**
- `AgentConfig` must reference LLM endpoint and model
- Support agent-specific endpoint overrides (future use)
- Pass runtime settings to `OpenAICompatibleRuntime`
- Respect `max_parallel_agents` in agent pools
