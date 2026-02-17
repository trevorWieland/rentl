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

## Validation Script

The `scripts/validate_scene_summarizer.py` script provides end-to-end validation of the context phase agent with real game data:

```bash
# Validate with sample data (no LLM call)
python scripts/validate_scene_summarizer.py --mock

# Validate with real LLM using rentl.toml config
python scripts/validate_scene_summarizer.py

# Validate with custom JSONL input
python scripts/validate_scene_summarizer.py --input scenes.jsonl

# Process scenes concurrently (3 separate agent calls)
python scripts/validate_scene_summarizer.py --input scenes.jsonl --concurrent

# Override model or API settings
python scripts/validate_scene_summarizer.py --model gpt-5-nano --api-key "your-key"
```

### JSONL Input Format

Input files should contain `SourceLine` records:

```json
{"line_id": "scene_001", "text": "Hello", "speaker": "Character", "scene_id": "scene_001", "route_id": "route_001"}
```

**Important:** IDs must match the `HumanReadableId` pattern: `^[a-z]+_[0-9]+$` (lowercase letters, underscore, numbers).

### Real-World Extraction Notes

When extracting from game engines:

- **Speaker pairing**: Some engines output speakers as separate lines before dialogue (e.g., "奈月" followed by line starting with 「). The validation script handles this by tracking state.
- **No-op lines**: Empty lines or placeholders like "名無し" are filtered out during extraction but tracked via metadata for reconstruction.
- **Scene grouping**: Lines are automatically grouped by `scene_id` for per-scene summarization.
- **Concurrent mode**: Use `--concurrent` to process multiple scenes in parallel with separate agent contexts.

### Configuration Requirements

The validation script reads from `rentl.toml`:

```toml
[endpoint]
provider_name = "local"
base_url = "http://localhost:1234/v1"
api_key_env = "RENTL_LOCAL_API_KEY"

[pipeline.default_model]
model_id = "qwen/qwen3-30b-a3b"
```

Environment variables are loaded from `.env` file if present.

## Standards Compliance

This package follows rentl Agent OS standards:

- **Async-first design** — All APIs use async/await
- **Strict typing** — No `Any` or `object`; explicit types with `ty` enforcement
- **Pydantic-only schemas** — All schemas use Pydantic with Field and validators
- **Adapter-interface protocol** — Agent harness implements protocols, not concrete implementations

## License

MIT
