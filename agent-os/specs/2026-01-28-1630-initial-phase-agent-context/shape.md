# Initial Phase Agent: Context (Scene Summarizer) — Shaping Notes

## Scope

Create the first agent in the rentl pipeline: a **Scene Summarization Agent** for the Context phase. This agent analyzes scenes from the source script and produces summaries with character identification, written in the source language.

This spec establishes foundational patterns that will be used by all future agents:
- Fully declarative agent profiles via TOML
- Three-layer prompt architecture
- Strict initialization validation
- Template variable system
- Tool integration framework

## Decisions

### Agent Type: Scene Summarizer
- Focused on scene summarization (not glossary or character bios for v0.1)
- Produces `SceneSummary` objects (scene_id, summary text, characters list)
- Writes output in the source language (context/pretranslation phases work in source)

### Processing Strategy: Scene-by-Scene
- Each agent invocation handles one scene
- Enables concurrent/parallel execution via PhaseAgentPool
- Requires scene_id to be pre-assigned on source lines

### Hard Requirements
- **scene_id required**: Agent fails with clear error if lines lack scene_id
- No silent fallbacks or approximations
- Suggests BatchSummarizer (v0.2+) for scene-less content

### Fully Declarative Agents via TOML
- Agents defined entirely in TOML configuration files
- No agent-specific Python code required
- Community can contribute agents by adding TOML files
- Enables easy prompt tuning and A/B testing

### Three-Layer Prompt Architecture
```
Root Layer (Project Context)
├── Game name, synopsis, genre
├── "You are part of a localization team..."
└── Runtime-injected from project config

Phase Layer (Context Team)
├── "Your team is the 'Context Building' team"
├── "All outputs must be in {source_lang}"
└── Phase-specific principles and goals

Agent Layer (Scene Summarizer)
├── "Your role is to summarize scenes..."
├── What makes a good summary, character identification
└── Output format requirements
```

### Template Variable System
- Closed set of allowed variables per layer/context
- Validated at load time (fail fast)
- Unknown variables cause initialization failure

### Provider-Agnostic Model Hints
- Model IDs are opaque strings
- No provider-specific sections (openrouter, openai, etc.)
- Capability-based hints (min_context_tokens, benefits_from_reasoning)

### Multi-Agent Orchestration (v0.2 Design)
- Priority field for execution order within phase
- depends_on field for agent dependencies in same phase
- Route summarizer would depend on scene summarizer

## Context

### Visuals
None provided

### References

#### 1. Agent Runtime Scaffold (Spec 14)
**Location:** `packages/rentl-agents/src/rentl_agents/harness.py`

**Relevance:** Provides base AgentHarness class that wraps pydantic-ai

**Key patterns:**
- AgentHarness[InputT, OutputT] with typed input/output
- Prompt template rendering via PromptRenderer
- Tool registration with pydantic-ai Agent
- Retry logic with exponential backoff

#### 2. Phase Schemas
**Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`

**Relevance:** Defines ContextPhaseInput/Output and SceneSummary

**Key patterns:**
- SceneSummary: scene_id, summary, characters
- ContextPhaseOutput: scene_summaries, context_notes, glossary

#### 3. Orchestrator Context Phase
**Location:** `packages/rentl-core/src/rentl_core/orchestrator.py` (lines 540-630)

**Relevance:** Shows how context phase is executed

**Key patterns:**
- Work chunking via _build_work_chunks
- Agent pool execution via _run_agent_pool
- Output merging via _merge_context_outputs

### Product Alignment

From `agent-os/product/roadmap.md`:
- Spec (15) depends on (14) Agent Runtime Scaffold
- Creates first agent enabling specs 16-20 (other phase agents)
- v0.1 targets "one agent per phase (minimal but complete)"
- v0.2 introduces multi-agent teams per phase

From `agent-os/product/mission.md`:
- Context phase builds understanding for translation quality
- Scene summaries help maintain coherence across script
- Output language in source enables proper source text analysis

## Standards Applied

- **testing/make-all-gate** — Verification required before completion
- **testing/three-tier-test-structure** — Unit tests in tests/unit/, integration in BDD
- **testing/test-timing-rules** — Unit <250ms, integration <5s
- **python/async-first-design** — Agent execution is async for LLM network IO
- **python/strict-typing-enforcement** — All schemas use strict Pydantic types
- **python/pydantic-only-schemas** — Input/output use Pydantic
- **architecture/adapter-interface-protocol** — Agent implements PhaseAgentProtocol
- **ux/frictionless-by-default** — Opinionated defaults, no config required to run

## Deferred to Future Versions

### v0.2+
- **Multi-agent orchestration**: Execute multiple agents per phase with priority/depends_on
- **Agent hooks**: Pre/post LLM callbacks for custom processing
- **BatchSummarizer**: Agent for content without scene boundaries
- **RouteSummarizer**: Route-level context building (depends on scene summaries)
- **Agent families**: Additional layer between phase and agent for grouped agents

### v1.0+
- **Template repo extraction**: Structure designed for copier template
- **Model recommendation UI**: Interactive model selection from hints
- **Community agent marketplace**: Share and discover agent profiles
