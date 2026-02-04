# Agent Runtime Scaffold (pydantic-ai) — Shaping Notes

## Scope

Full agent runtime scaffold powered by pydantic-ai to enable phase agents in the localization pipeline. This scaffold provides:
- Agent base protocol and harness for pydantic-ai integration
- Prompt template system with variable substitution and context injection
- Tool plumbing and registration framework
- Agent factory for instantiating phase agents
- Integration with existing `PhaseAgentPool` in orchestrator

## Decisions

### Package Structure
- Create new `rentl-agents` package to house agent runtime logic
- Follow existing package structure: `src/rentl_agents/` with `pyproject.toml`
- Dependencies: `pydantic-ai`, `rentl-core`, `rentl-schemas`, `rentl-llm`

### Agent Harness Design
- Base `AgentHarness[InputT, OutputT]` class implements `PhaseAgentProtocol`
- Reuse existing `OpenAICompatibleRuntime` from `rentl-llm`
- Wrap pydantic-ai `Agent` with additional functionality:
  - Prompt template rendering
  - Tool registration
  - Error handling with retries
  - Input/output validation

### Prompt Template System
- Template strings with `{{variable}}` syntax for substitution
- Context injection: project context, style guide, glossary, scene summaries
- Template caching for performance
- Type-safe variable substitution

### Tool System
- `AgentToolProtocol` defines tool contract
- Built-in tools: context lookup, glossary search, style guide retrieval
- Tools registered with pydantic-ai `Agent` via decorators
- Tool execution with error handling and validation

### Agent Factory
- `AgentFactory` creates `AgentHarness` instances from configuration
- Support for agent pool creation via `PhaseAgentPool.from_factory()`
- Agent configuration schema: model, prompts, tools, retry policy

### Integration Points
- `AgentHarness` implements `PhaseAgentProtocol` from `rentl-core.ports.orchestrator`
- Agent pools passed to `PipelineOrchestrator` constructor
- Uses existing `OpenAICompatibleRuntime` for LLM calls

## Context

### Visuals
None provided

### References

#### 1. OpenAI Runtime (rentl-llm)
**Location:** `packages/rentl-llm/src/rentl_llm/openai_runtime.py`

**Relevance:** Already implements pydantic-ai integration with OpenAI-compatible endpoints

**Key patterns to borrow:**
- Uses `pydantic_ai.Agent` with model and instructions
- Integrates with `OpenAIProvider` and `OpenAIChatModel`
- Handles model settings (temperature, top_p, reasoning_effort, etc.)
- Returns structured `LlmPromptResponse`

#### 2. Phase Agent Protocols (rentl-core)
**Location:** `packages/rentl-core/src/rentl_core/ports/orchestrator.py`

**Relevance:** Defines `PhaseAgentProtocol` and `PhaseAgentPoolProtocol` that agent harness must implement

**Key patterns to borrow:**
- `PhaseAgentProtocol[InputT, OutputT]` with `run(payload: InputT) -> OutputT` method
- `PhaseAgentPoolProtocol[InputT, OutputT]` with `run_batch(payloads: list[InputT]) -> list[OutputT]` method
- Phase-specific type aliases: `ContextAgentProtocol`, `TranslateAgentProtocol`, etc.

#### 3. PhaseAgentPool Implementation (rentl-core)
**Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`

**Relevance:** Shows how agent pools are used in the orchestrator

**Key patterns to borrow:**
- `PhaseAgentPool` class with `agents` list and `max_parallel` setting
- `from_factory()` class method for creating pools from a factory
- Async execution with semaphore for concurrency control
- Preserves output ordering aligned with input order

### Product Alignment

From `agent-os/product/roadmap.md`:
- Spec (14) enables subsequent phase agent implementations (15-20)
- Provides foundational infrastructure for Context, Pretranslation, Translate, QA, Edit agents
- Supports BYOK model configuration (already implemented in spec 12-13)
- Integrates with existing orchestrator and phase execution framework

## Standards Applied

- **testing/make-all-gate** — Verification required before completion; must run `make all` and fix failures
- **python/async-first-design** — All APIs use async/await for efficient LLM network IO
- **python/strict-typing-enforcement** — No `Any` or `object` in types; all Pydantic fields use Field with description
- **python/pydantic-only-schemas** — All schemas use Pydantic with Field and validators
- **architecture/adapter-interface-protocol** — Agent harness implements protocols; core depends on interfaces not implementations

## Implementation Notes

### Key Dependencies
- `pydantic-ai` — Main agent runtime framework
- `rentl-core.ports.orchestrator.PhaseAgentProtocol` — Agent harness implements this
- `rentl-core.ports.llm.LlmRuntimeProtocol` — LLM runtime interface (already implemented)
- `rentl-schemas.phases.*PhaseInput/Output` — Phase input/output schemas
- `rentl-llm.OpenAICompatibleRuntime` — LLM runtime implementation

### Testing Strategy
- Unit tests with >80% coverage
- Mock `OpenAICompatibleRuntime` for fast tests (<250ms per test)
- Mock pydantic-ai `Agent` for isolated unit tests
- Integration tests and quality tests deferred to future specs (24-25)

### Manual Validation
- Temporary Python scripts to test agent harness instantiation
- Verify prompt template substitution with test data
- Verify tool registration and execution flow
- Verify agent factory creates valid instances
- Verify agent pool integration works
