# Agent Runtime Scaffold (pydantic-ai) — Implementation Plan

**Spec ID:** 14
**Created:** 2026-01-27
**Status:** Implementation Complete ✓

## Overview

Establish the agent runtime scaffold powered by pydantic-ai to enable phase agents in the localization pipeline. This scaffold provides a base harness for agent execution, prompt management, tool integration, and agent factory patterns.

## Scope

Full agent runtime scaffold including:
- Agent base protocol and harness
- Prompt template system
- Tool plumbing and registration
- Agent factory for instantiation
- Integration with existing PhaseAgentPool
- Unit test coverage >80%

## Dependencies

- Spec (01) Schema Definitions & Validation — Pydantic schemas for configs, inputs, outputs
- Spec (12) BYOK Config & Endpoint Validation — Model endpoint validation
- Spec (13) BYOK Runtime Integration — OpenAI-compatible runtime clients (pydantic-ai)

---

## Task 1: Save Spec Documentation ✓

Create `agent-os/specs/2026-01-27-2155-agent-runtime-scaffold/` with:
- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context from our conversation)
- **standards.md** — Relevant standards that apply to this work
- **references.md** — Pointers to reference implementations studied
- **visuals/** — Any mockups or screenshots provided (none for this feature)

**Status:** Completed

---

## Task 2: Create Agent Runtime Package Structure ✓

Create `rentl-agents` package with proper Python package structure:

### Package Structure
```
rentl-agents/
├── pyproject.toml
├── README.md
├── src/
│   └── rentl_agents/
│       ├── __init__.py
│       ├── harness.py
│       ├── prompts.py
│       ├── tools.py
│       └── factory.py
└── tests/
    ├── __init__.py
    ├── test_harness.py
    ├── test_prompts.py
    ├── test_tools.py
    └── test_factory.py
```

### Dependencies
- `pydantic-ai` — Agent runtime framework
- `rentl-core` — Phase protocols and orchestrator
- `rentl-schemas` — Phase schemas and primitives
- `rentl-llm` — OpenAI-compatible runtime
- `pytest` — Testing framework
- `pytest-asyncio` — Async test support

**Status:** Completed

---

## Task 3: Define Agent Base Protocol and Harness ✓

Create base agent protocol and runtime harness:

### Key Components

#### `AgentHarnessProtocol`
Protocol defining the agent wrapper contract:
- `run(payload: InputT) -> OutputT` — Execute agent with input
- `initialize(config: AgentConfig) -> None` — Configure agent
- `validate_input(input: InputT) -> bool` — Validate input schema
- `validate_output(output: OutputT) -> bool` — Validate output schema

#### `AgentHarness[InputT, OutputT]`
Base implementation with:
- LLM runtime integration using `OpenAICompatibleRuntime`
- Prompt template management via `PromptRenderer`
- Tool registration with pydantic-ai `Agent`
- Error handling with retry logic (exponential backoff)
- Structured logging for agent execution

#### Agent Lifecycle
1. **Initialize**: Load config, setup prompt templates, register tools
2. **Validate Input**: Schema validation before execution
3. **Execute**: Call LLM via pydantic-ai with context and tools
4. **Validate Output**: Schema validation after execution
5. **Error Handling**: Retry on transient failures, log errors

**Status:** Completed

---

## Task 4: Implement Prompt Template System ✓

Create prompt template management:

### Components

#### `PromptTemplate`
Schema with:
- Template string with `{{variable}}` substitution
- Variable definitions with types and descriptions
- Default values for optional variables
- Template metadata (name, version, description)

#### `PromptRenderer`
Template renderer with:
- Variable substitution from context data
- Type conversion and validation
- Template caching for performance
- Error handling for missing variables

#### Context Injection
- Project context (high-level description)
- Style guide (writing guidelines)
- Glossary terms (term translations)
- Scene context (scene summaries, character notes)

**Status:** Completed

---

## Task 5: Implement Tool Plumbing and Registration ✓

Create tool system for agent capabilities:

### Components

#### `AgentToolProtocol`
Protocol defining tool contract:
- `name: str` — Tool identifier
- `description: str` — Tool description for LLM
- `execute(input: dict[str, Any]) -> Any` — Tool execution
- `schema: dict[str, Any]` — Input/output schemas

#### Built-in Tools
1. **Context Lookup** — Retrieve scene summaries and notes
2. **Glossary Search** — Search glossary terms by keyword
3. **Style Guide Lookup** — Retrieve style guide sections
4. **Character Reference** — Get character bios and notes

#### Tool Registration
- Register tools with pydantic-ai `Agent`
- Tool execution with error handling
- Output validation against schemas
- Tool result caching

**Status:** Completed

---

## Task 6: Create Agent Factory and Pool Integration ✓

Create factory for instantiating phase agents:

### Components

#### `AgentConfig`
Configuration schema with:
- Model endpoint reference
- System prompt template
- User prompt template
- Tool names to register
- Retry policy (max retries, backoff base)

#### `AgentFactory`
Factory methods:
- `create_agent[InputT, OutputT](config: AgentConfig) -> AgentHarness[InputT, OutputT]`
- `create_pool[InputT, OutputT](config: AgentConfig, count: int) -> PhaseAgentPoolProtocol`
- Agent instance caching for performance

#### PhaseAgentPool Integration
- Wrap `AgentHarness` in `PhaseAgentPool`
- Support for `PhaseAgentPool.from_factory()`
- Pass agent pool to `PipelineOrchestrator`
- Enable concurrent agent execution

**Status:** Completed

---

## Task 7: Add Unit Tests (>80% coverage) ✓

Write comprehensive unit tests:

### Test Coverage

#### `test_harness.py`
- Test agent initialization with config
- Test input validation
- Test execution with mocked LLM runtime
- Test output validation
- Test error handling and retries
- Test prompt template injection

#### `test_prompts.py`
- Test prompt template parsing
- Test variable substitution
- Test type conversion
- Test context injection
- Test template caching

#### `test_tools.py`
- Test tool registration
- Test tool execution
- Test tool error handling
- Test built-in tools (context, glossary, style guide)
- Test tool output validation

#### `test_factory.py`
- Test agent creation from config
- Test agent pool creation
- Test agent instance caching
- Test factory error handling
- Test PhaseAgentPool integration

### Mocking Strategy
- Mock `OpenAICompatibleRuntime` for fast tests (<250ms)
- Mock `Agent` from pydantic-ai
- Use pytest fixtures for common test data
- Async test support with pytest-asyncio

**Status:** Completed

---

## Task 8: Verification - Run make all ✓

Run `make all` to ensure all code passes quality checks:

### Quality Checks
- Format code with ruff (`ruff format`)
- Check linting rules (`ruff check`)
- Type check with ty (`ty check`)
- Run unit tests (`pytest --cov=rentl_agents`)

### Manual Validation Steps

#### Validation Script 1: Agent Harness Instantiation
```python
# Create temporary script to test agent harness
# Verify initialization, config loading, prompt rendering
```

#### Validation Script 2: Tool Registration
```python
# Test tool registration and execution
# Verify built-in tools work correctly
```

#### Validation Script 3: Agent Factory
```python
# Test agent factory creates valid instances
# Verify agent pool integration
```

**Status:** Completed

---

## Summary

The Agent Runtime Scaffold is now complete and provides:
- Base `AgentHarness` protocol and implementation
- Prompt template system with variable substitution
- Tool registration and execution framework
- Agent factory for creating phase agents
- Full integration with existing `PhaseAgentPool`
- Comprehensive unit test coverage (>80%)
- All quality checks passing (format, lint, type, tests)

This scaffold enables the implementation of phase agents (Context, Pretranslation, Translate, QA, Edit) in subsequent specs (15-20).

## Success Criteria

✓ All unit tests pass with >80% coverage
✓ `make all` passes (format, lint, type, tests)
✓ Manual validation scripts execute successfully
✓ Agent harness integrates with PhaseAgentPool
✓ Prompt templates render correctly
✓ Tools register and execute properly
✓ Agent factory creates valid instances
