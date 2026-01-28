# rentl-agents

Agent runtime scaffold for rentl phase agents powered by pydantic-ai.

## Overview

This package provides the foundational infrastructure for creating phase agents in the rentl localization pipeline:

- **Agent Harness** — Base protocol and implementation for agent execution
- **Prompt Templates** — Template system with variable substitution and context injection
- **Tool System** — Tool registration and execution framework
- **Agent Factory** — Factory for instantiating phase agents and pools

## Installation

```bash
uv add rentl-agents
```

## Usage

### Creating an Agent

```python
from rentl_agents import AgentFactory, AgentConfig
from rentl_schemas.phases import ContextPhaseInput, ContextPhaseOutput

config = AgentConfig(
    model_endpoint_ref="default",
    system_prompt="You are a context analysis agent.",
    user_prompt_template="Analyze these scenes: {{scenes}}",
    tools=["context_lookup"],
)

factory = AgentFactory()
agent = factory.create_agent[ContextPhaseInput, ContextPhaseOutput](config)

result = await agent.run(input_payload)
```

### Creating an Agent Pool

```python
from rentl_agents import AgentFactory
from rentl_core.ports.orchestrator import PhaseAgentPoolProtocol

factory = AgentFactory()
pool = factory.create_pool[ContextPhaseInput, ContextPhaseOutput](
    config=config,
    count=4,
    max_parallel=2,
)

results = await pool.run_batch(input_payloads)
```

## Architecture

### Agent Harness

The `AgentHarness[InputT, OutputT]` class implements the `PhaseAgentProtocol` interface, providing:

- LLM runtime integration via `OpenAICompatibleRuntime`
- Prompt template rendering with context injection
- Tool registration and execution
- Error handling with retry logic
- Input/output validation

### Prompt Templates

Prompt templates use `{{variable}}` syntax for substitution:

```python
template = "Translate this text: {{text}} from {{source_lang}} to {{target_lang}}"
context = {"text": "Hello world", "source_lang": "en", "target_lang": "ja"}
rendered = render_template(template, context)
# Result: "Translate this text: Hello world from en to ja"
```

### Tools

Built-in tools provide agent capabilities:

- `context_lookup` — Retrieve scene summaries and context notes
- `glossary_search` — Search glossary terms by keyword
- `style_guide_lookup` — Retrieve style guide sections
- `character_reference` — Get character bios and notes

### Agent Factory

The `AgentFactory` creates configured agent instances and pools:

- `create_agent[InputT, OutputT](config)` — Create single agent
- `create_pool[InputT, OutputT](config, count)` — Create agent pool
- Agent instance caching for performance

## Standards Compliance

This package follows rentl Agent OS standards:

- **Async-first design** — All APIs use async/await
- **Strict typing** — No `Any` or `object`; explicit types with `ty` enforcement
- **Pydantic-only schemas** — All schemas use Pydantic with Field and validators
- **Adapter-interface protocol** — Agent harness implements protocols, not concrete implementations

## License

MIT
