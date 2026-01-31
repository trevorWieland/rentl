# Spec (15): Initial Phase Agent — Context (Scene Summarizer)

**Roadmap Item:** (15) Initial Phase Agent: Context
**Created:** 2026-01-28
**Status:** Implementation In Progress

---

## Overview

Create the first agent in the rentl pipeline using a **fully declarative architecture**. Agents are defined via TOML configuration, validated strictly at load time, and executed by a generic runtime engine.

This spec establishes foundational patterns for all future agents:
- Three-layer prompt architecture (root → phase → agent)
- TOML-based agent profiles with versioning
- Strict validation at initialization
- Tool system integration
- Template variable validation

---

## Design Decisions

### 1. Fully Declarative Agents via TOML

Agents are **configuration, not code**:

```toml
# agents/context/scene_summarizer.toml

[meta]
name = "scene_summarizer"
version = "1.0.0"
phase = "context"
description = "Analyzes scenes and produces summaries with character identification"
output_schema = "SceneSummary"

[requirements]
scene_id_required = true

[orchestration]
priority = 10
depends_on = []

[prompts.agent]
content = """..."""

[prompts.user_template]
content = """
Scene ID: {{scene_id}}
{{scene_lines}}
"""

[tools]
allowed = ["get_game_info"]

[model_hints]
recommended = ["gpt-5.2", "claude-3.5-sonnet", "nemotron-3-nano-30b-a3b"]
min_context_tokens = 8192
benefits_from_reasoning = false
```

**Benefits:**
- Community can contribute agents by adding TOML files
- No Python knowledge required to tune/create agents
- Full reproducibility and versioning
- Easy A/B testing by swapping profiles

### 2. Three-Layer Prompt Architecture

```
Root Layer → Phase Layer → Agent Layer
     ↓              ↓              ↓
  Project      Context Team    Scene Summarizer
  framing      + source lang   specific task
```

- **Root layer**: Project name, synopsis, localization team framing
- **Phase layer**: Team role, source language output, phase principles
- **Agent layer**: Task-specific instructions

### 3. Template Variable System

Closed set of allowed variables, validated at load time:

| Layer | Allowed Variables |
|-------|-------------------|
| Root | `game_name`, `game_synopsis` |
| Phase (context) | `source_lang` |
| Agent (scene_summarizer) | `scene_id`, `line_count`, `scene_lines` |

### 4. Strict Initialization Validation

All errors caught at load time:
- Pydantic strict mode (no extra fields, type enforcement)
- Template variable validation against allowed set
- Schema reference resolution to real Pydantic class
- Tool name resolution to registered tools

### 5. Provider-Agnostic Model Hints

Model IDs are opaque strings (no provider-specific sections):

```toml
[model_hints]
recommended = ["gpt-5.2", "nemotron-3-nano-30b-a3b"]
min_context_tokens = 8192
```

### 6. Multi-Agent Orchestration Design (v0.2 Prep)

Schema supports priority and dependencies for future use:

```toml
[orchestration]
priority = 10  # Lower = earlier
depends_on = []  # List of agent names in same phase
```

### 7. Scene Validation Requirement

Scene Summarizer requires `scene_id` on all source lines:
- Hard validation at initialization
- Clear error message suggesting BatchSummarizer for scene-less content
- No silent fallbacks or approximations

---

## Task List

### Task 1: Save Spec Documentation ✓

Create `agent-os/specs/2026-01-28-1630-initial-phase-agent-context/` with:
- plan.md (this file)
- shape.md
- standards.md
- references.md

---

### Task 2: Design Agent Profile Schema

**File:** `packages/rentl-schemas/src/rentl_schemas/agents.py`

**Components:**
- `AgentProfileMeta` — name, version, phase, output_schema
- `AgentRequirements` — scene_id_required, other validations
- `AgentOrchestration` — priority, depends_on (v0.2 prep)
- `AgentPromptConfig` — agent prompt, user template
- `ToolAccessConfig` — allowed tool list
- `ModelHints` — recommended models, context requirements
- `AgentProfileConfig` — full validated profile

**Validation:**
- `ConfigDict(strict=True, extra="forbid")`
- All string refs resolve at load time

---

### Task 3: Implement Template Variable System

**File:** `packages/rentl-agents/src/rentl_agents/templates.py`

**Components:**
- `ALLOWED_VARIABLES` — registry of valid variables per context
- `TemplateValidator` — validates templates at load time
- `TemplateRenderer` — renders templates with runtime values
- `TemplateValidationError` — raised for unknown variables

---

### Task 4: Implement Agent Profile Loader

**File:** `packages/rentl-agents/src/rentl_agents/profiles/loader.py`

**Components:**
- `AgentProfileLoader` — loads TOML → validated config
- Schema resolution: `output_schema` string → class
- Tool resolution: tool names → registered tools
- Discovery: scans `agents/{phase}/` directories

**Validation chain:**
1. TOML parse
2. Pydantic validation (strict)
3. Template variable validation
4. Schema name resolution
5. Tool name resolution

---

### Task 5: Implement Prompt Layer System

**File:** `packages/rentl-agents/src/rentl_agents/layers.py`

**Files:**
- `prompts/root.toml` — project framing
- `prompts/phases/context.toml` — context team + source lang

**Components:**
- `PromptLayerRegistry` — stores layer prompts
- `PromptComposer` — composes final system prompt

---

### Task 6: Create Default Profiles

**Files:**
- `agents/context/scene_summarizer.toml`
- `prompts/root.toml`
- `prompts/phases/context.toml`

---

### Task 7: Implement Profile-Driven Agent Runtime

**File:** `packages/rentl-agents/src/rentl_agents/runtime.py`

**Components:**
- `ProfileAgent` — generic agent from TOML profile
- Prompt composition from three layers
- pydantic-ai structured output
- Retry logic for schema validation failures

---

### Task 8: Implement Tool System

**Files:**
- `packages/rentl-agents/src/rentl_agents/tools/registry.py`
- `packages/rentl-agents/src/rentl_agents/tools/game_info.py`

**Components:**
- `ToolRegistry` — tool name → implementation
- `get_game_info` tool — returns project context

---

### Task 9: Implement Scene Validation

**File:** `packages/rentl-agents/src/rentl_agents/context/__init__.py`

**Components:**
- `validate_scene_input()` — require scene_id
- `SceneValidationError` — clear error message

---

### Task 10: Wire to Orchestrator

**Updates:** orchestrator integration with profile-loaded agents

---

### Task 11: Unit Tests (>80% coverage)

**Coverage:**
- Profile loading and validation
- Template variable validation
- Prompt layer composition
- Runtime execution (mocked LLM)
- Scene validation
- Tool registry

---

### Task 12: Integration Tests (BDD)

**Scenarios:**
- Load agent from TOML profile
- Validate template variables
- Fail on unknown variables
- Summarize scene with mock LLM
- Fail on missing scene_id

---

### Task 13: Manual Validation Script

**File:** `scripts/validate_scene_summarizer.py`

**Usage:**
```bash
python scripts/validate_scene_summarizer.py \
  --input ~/my-game/scenes.jsonl \
  --model gpt-5.2
```

---

### Task 14: Verification - Run make all

Run `make all` to ensure all code passes quality checks.

---

## Success Criteria

1. Agents defined entirely in TOML
2. Strict validation catches all config errors at init
3. Template variables validated against closed set
4. Three-layer prompts compose correctly
5. Structured output via pydantic-ai
6. Tool system demonstrated with get_game_info
7. Manual validation with real LLM
8. Unit tests >80%
9. Integration tests pass
10. `make all` passes
