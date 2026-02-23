# Declarative Agent Config

Agents are defined as TOML configuration, not code. Every agent profile is a TOML file validated against Pydantic schemas at load time, enabling community contribution, prompt tuning, and version tracking without touching Python.

## Agent Profile Schema

A profile is validated by `AgentProfileConfig` (`rentl_schemas/agents.py`). Required top-level sections:

| TOML section      | Pydantic model           | Required |
|-------------------|--------------------------|----------|
| `[meta]`          | `AgentProfileMeta`       | yes      |
| `[requirements]`  | `AgentRequirements`      | no (defaults) |
| `[orchestration]` | `AgentOrchestration`     | no (defaults) |
| `[prompts]`       | `AgentPromptConfig`      | yes      |
| `[tools]`         | `ToolAccessConfig`       | no (defaults) |
| `[model_hints]`   | `ModelHints`             | no (defaults) |

## TOML File Structure

### Directory layout

```
agents/
├── context/
│   └── scene_summarizer.toml
├── pretranslation/
│   └── idiom_labeler.toml
├── translate/
│   └── direct_translator.toml
├── qa/
│   └── style_guide_critic.toml
└── edit/
    └── basic_editor.toml
```

Agents live in `agents/{phase}/` subdirectories. The loader (`discover_agent_profiles` in `rentl_agents/profiles/loader.py`) scans each phase directory and validates that `meta.phase` matches the directory name. Mismatches raise `AgentProfileLoadError`.

### `[meta]` section

| TOML key        | Pydantic field                | Type        | Constraints                              |
|-----------------|-------------------------------|-------------|------------------------------------------|
| `name`          | `AgentProfileMeta.name`       | `str`       | 1-64 chars, `^[a-z][a-z0-9_]*$` (snake_case) |
| `version`       | `AgentProfileMeta.version`    | `str`       | `^\d+\.\d+\.\d+$` (semver), min 5 chars |
| `phase`         | `AgentProfileMeta.phase`      | `PhaseName` | One of: `context`, `pretranslation`, `translate`, `qa`, `edit` |
| `description`   | `AgentProfileMeta.description`| `str`       | 1-500 chars                              |
| `output_schema` | `AgentProfileMeta.output_schema` | `str`    | `^[A-Z][a-zA-Z0-9]*$` (PascalCase), must be in `SCHEMA_REGISTRY` |

The `output_schema` value must resolve via `resolve_output_schema()` in `loader.py`. Registered schemas are initialized in `_init_schema_registry()` and include: `SceneSummary`, `IdiomAnnotation`, `IdiomAnnotationList`, `IdiomReviewLine`, `TranslationResultList`, `TranslationResultLine`, `StyleGuideViolation`, `StyleGuideViolationList`, `StyleGuideReviewList`.

### `[requirements]` section

| TOML key             | Pydantic field                       | Type   | Default |
|----------------------|--------------------------------------|--------|---------|
| `scene_id_required`  | `AgentRequirements.scene_id_required`| `bool` | `false` |

### `[orchestration]` section

| TOML key      | Pydantic field                       | Type        | Default | Constraints |
|---------------|--------------------------------------|-------------|---------|-------------|
| `priority`    | `AgentOrchestration.priority`        | `int`       | `10`    | 1-100, lower = earlier |
| `depends_on`  | `AgentOrchestration.depends_on`      | `list[str]` | `[]`    | Valid agent names; self-dependency forbidden |

### `[prompts]` section

Contains two sub-tables:

| TOML key                     | Pydantic field                        | Type  |
|------------------------------|---------------------------------------|-------|
| `[prompts.agent].content`    | `AgentPromptConfig.agent.content`     | `str` |
| `[prompts.user_template].content` | `AgentPromptConfig.user_template.content` | `str` |

Both are required and non-empty. Content may contain `{{variable}}` placeholders validated against the phase's allowed variable set (see Template Variable Registry below).

### `[tools]` section

| TOML key   | Pydantic field             | Type        | Default |
|------------|----------------------------|-------------|---------|
| `allowed`  | `ToolAccessConfig.allowed` | `list[str]` | `[]`    |
| `required` | `ToolAccessConfig.required`| `list[str]` | `[]`    |

**Invariant:** `required` must be a subset of `allowed` (enforced by `validate_required_subset` model validator). Tool names must match `^[a-z_]+$` (alphanumeric + underscore). When `required` tools are configured, the runtime uses `end_strategy="exhaustive"` and gates output tools until all required tools have been called.

### `[model_hints]` section

| TOML key                   | Pydantic field                          | Type        | Default |
|----------------------------|-----------------------------------------|-------------|---------|
| `recommended`              | `ModelHints.recommended`                | `list[str]` | `[]`    |
| `min_context_tokens`       | `ModelHints.min_context_tokens`         | `int\|None` | `None`  |
| `benefits_from_reasoning`  | `ModelHints.benefits_from_reasoning`    | `bool`      | `false` |

Model IDs in `recommended` are provider-agnostic opaque strings. `min_context_tokens` must be >= 1024 when set.

## Layered Prompt System

Prompts compose three layers at runtime via `PromptComposer` (`rentl_agents/layers.py`):

```
Root layer  →  Phase layer  →  Agent layer
(project)      (team role)     (specific task)
```

### Root layer

File: `prompts/root.toml`
Schema: `RootPromptConfig` (`rentl_schemas/agents.py`)

```toml
[system]
content = "You are part of a professional game localization team working on {{game_name}}..."
```

Single `[system].content` field with project-level framing. Uses root-layer variables only.

### Phase layer

Files: `prompts/phases/{phase}.toml`
Schema: `PhasePromptConfig` (`rentl_schemas/agents.py`)

```toml
phase = "context"
output_language = "source"

[system]
content = "You are on the Context Building team..."
```

| TOML key          | Pydantic field                     | Constraints |
|-------------------|------------------------------------|-------------|
| `phase`           | `PhasePromptConfig.phase`          | Must be a valid `PhaseName` |
| `output_language` | `PhasePromptConfig.output_language`| `"source"` or `"target"` |
| `[system].content`| `PhasePromptConfig.system.content` | Non-empty string |

### Agent layer

Defined inline in the agent profile TOML under `[prompts.agent]` and `[prompts.user_template]`. The system prompt from `[prompts.agent].content` is the agent-specific instruction appended after root and phase system prompts. The `[prompts.user_template].content` is the per-invocation user message.

### Composition order

The final system prompt concatenates: root system → phase system → agent system. The user prompt is rendered from the agent's `user_template`. All layers go through template variable substitution before assembly.

## Template Variable Registry

Template variables use `{{variable_name}}` syntax. Validation happens at profile load time via `validate_template()` in `rentl_agents/templates.py`.

### Variables by layer

| Layer                | Variables                                                    | Source constant                    |
|----------------------|--------------------------------------------------------------|------------------------------------|
| Root                 | `game_name`, `game_synopsis`                                 | `ROOT_LAYER_VARIABLES`             |
| Phase (added to root)| `source_lang`, `target_lang`                                | `PHASE_LAYER_VARIABLES`            |
| Agent: context       | `scene_id`, `line_count`, `scene_lines`, `alignment_feedback`| `CONTEXT_AGENT_VARIABLES`          |
| Agent: pretranslation| `scene_id`, `line_count`, `source_lines`, `scene_summary`, `alignment_feedback` | `PRETRANSLATION_AGENT_VARIABLES` |
| Agent: translate     | `scene_id`, `line_count`, `source_lines`, `annotated_source_lines`, `scene_summary`, `pretranslation_notes`, `glossary_terms`, `alignment_feedback` | `TRANSLATE_AGENT_VARIABLES` |
| Agent: qa            | `line_id`, `source_text`, `translated_text`, `scene_summary`, `glossary_terms`, `style_guide`, `lines_to_review`, `alignment_feedback` | `QA_AGENT_VARIABLES` |
| Agent: edit          | `line_id`, `source_text`, `translated_text`, `qa_issues`, `scene_summary`, `alignment_feedback` | `EDIT_AGENT_VARIABLES` |

Agent-layer templates may use variables from all three layers (root + phase + agent). Rendering uses `TemplateContext` with root → phase → agent precedence (later layers override).

## Tool Registration & Access Control

Tools are managed by `ToolRegistry` (`rentl_agents/tools/registry.py`). The profile's `[tools].allowed` list determines which registered tools the agent can call. `[tools].required` gates structured output until those tools have been invoked.

### Runtime enforcement

1. `allowed` tools are passed to `pydantic_ai.Agent(tools=...)` as callables
2. `required` tools trigger `end_strategy="exhaustive"` and a `prepare_output_tools` callback that hides output tools until all required tools appear in the message history
3. Tool names must be alphanumeric + underscore, validated at load time

## Model Hints

The `[model_hints]` section provides advisory information for model selection. These are **hints, not constraints** — the runtime uses whatever model is configured in `rentl.toml`, but hints guide users toward appropriate models.

- `recommended`: Provider-agnostic model IDs that work well for this agent's task
- `min_context_tokens`: Minimum context window needed (helps warn about undersized models)
- `benefits_from_reasoning`: Whether extended thinking/reasoning modes improve output quality

## Orchestration Config

The `[orchestration]` section controls multi-agent execution order within a phase:

- `priority` (1-100): Lower values execute first. Default is 10.
- `depends_on`: List of agent names that must complete before this agent runs.

Self-dependency is forbidden (validated by `AgentProfileConfig.validate_profile`). The orchestrator resolves agents for a phase via `get_agents_for_phase()` which sorts by priority.

## Pipeline Phase Config

Pipeline phases are configured in `rentl.toml` under `[[pipeline.phases]]` and validated by `PhaseConfig` / `PipelineConfig` (`rentl_schemas/config.py`).

| TOML key      | Pydantic field              | Description |
|---------------|-----------------------------|-------------|
| `phase`       | `PhaseConfig.phase`         | Phase name (`PhaseName` enum) |
| `enabled`     | `PhaseConfig.enabled`       | Whether the phase runs (default: `true`) |
| `agents`      | `PhaseConfig.agents`        | Ordered list of agent names to execute |
| `model`       | `PhaseConfig.model`         | Phase-specific `ModelSettings` override |
| `concurrency` | `PhaseConfig.concurrency`   | Phase-specific concurrency override |
| `retry`       | `PhaseConfig.retry`         | Phase-specific retry override |
| `execution`   | `PhaseConfig.execution`     | Sharding/fan-out config (`PhaseExecutionConfig`) |
| `parameters`  | `PhaseConfig.parameters`    | Phase-specific parameter bag |

**Rules:**
- LLM phases (`context`, `pretranslation`, `translate`, `qa`, `edit`) must have `agents` configured when enabled
- Non-LLM phases (`ingest`, `export`) must not have `agents`
- Phases must follow canonical order: ingest → context → pretranslation → translate → qa → edit → export
- Phase names must be unique within the pipeline
- If `default_model` is unset, every enabled phase must specify its own `model`

Agent names in `PhaseConfig.agents` must match names discovered from the agents directory. The wiring layer (`rentl_agents/wiring.py`) resolves each name to a loaded profile and constructs the appropriate phase-specific wrapper agent.
