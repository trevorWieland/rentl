# Architecture Overview

This document describes rentl's internal architecture for contributors. It covers the pipeline, package structure, agent system, data flow, and storage model.

---

## Package Structure

rentl is a monorepo with 5 library packages and 3 service packages:

| Package | Location | Purpose |
|---|---|---|
| `rentl-schemas` | `packages/rentl-schemas/` | Pydantic data models shared across all packages |
| `rentl-core` | `packages/rentl-core/` | Pipeline orchestrator, port interfaces, QA runner |
| `rentl-agents` | `packages/rentl-agents/` | Agent runtime, TOML profiles, prompt composition |
| `rentl-llm` | `packages/rentl-llm/` | BYOK LLM integration (OpenAI-compatible endpoints) |
| `rentl-io` | `packages/rentl-io/` | I/O adapters: ingest, export, storage, logging |
| `rentl` (CLI) | `services/rentl-cli/` | Command-line interface (Typer + Rich) |
| `rentl-api` | `services/rentl-api/` | REST API (FastAPI + Uvicorn) |
| `rentl-tui` | `services/rentl-tui/` | Terminal UI (Textual) — scaffold only in v0.1 |

Dependency direction flows downward: service packages depend on library packages. `rentl-schemas` has no internal dependencies. `rentl-core` depends on `rentl-schemas`. Other library packages depend on `rentl-schemas` and `rentl-core`; `rentl-agents` also depends on `rentl-llm`.

---

## 7-Phase Pipeline

Every translation run passes through seven phases in order. The `PhaseName` enum in `rentl_schemas.primitives` defines them:

```
ingest → context → pretranslation → translate → qa → edit → export
```

| Phase | What it does | Language-specific? |
|---|---|---|
| **ingest** | Reads source files into `SourceLine` objects | No |
| **context** | Summarizes scenes for downstream agents | No |
| **pretranslation** | Labels idioms and cultural references | No |
| **translate** | Produces `TranslatedLine` objects from source | Yes (per language) |
| **qa** | Reviews translations for quality issues | Yes (per language) |
| **edit** | Applies QA feedback to improve translations | Yes (per language) |
| **export** | Writes final translations to output files | Yes (per language) |

Language-specific phases run once per target language. The `PIPELINE_PHASE_ORDER` list in `rentl_schemas.primitives` defines the canonical execution order.

---

## Orchestrator

The `PipelineOrchestrator` class in `rentl_core.orchestrator` drives phase execution.

### Run Flow

1. **Plan** — `run_plan()` builds an execution plan from enabled phases and target languages
2. **Execute** — Each phase runs in order. Language-specific phases fan out per language
3. **Skip** — Phases with existing non-stale results are skipped (staleness detection)
4. **Persist** — After each phase, results are saved to run state and artifacts
5. **Progress** — `ProgressUpdate` events stream to the progress sink throughout

### Key Types

- `PipelineRunContext` — Mutable run state: config, source lines, phase outputs, phase history, progress
- `PhaseRunRecord` — Immutable record of one phase execution: phase, revision, status, dependencies, artifacts
- `PhaseDependency` — Links a phase to the revision of an upstream phase it consumed
- `RunProgress` / `PhaseProgress` — Weighted progress tracking with ETA estimation

### Staleness Detection

Each `PhaseRunRecord` tracks its `dependencies` (upstream phase + revision). When an upstream phase is re-run, downstream records are marked `stale=True`. The orchestrator re-runs stale phases instead of skipping them. This replaces arbitrary circuit breakers with data-driven invalidation.

---

## Agent Architecture

Agents perform the LLM-powered work in the context, pretranslation, translate, qa, and edit phases. The ingest and export phases use deterministic adapters instead.

### TOML Profiles

Each agent is defined by a TOML file in `packages/rentl-agents/src/rentl_agents/agents/{phase}/`:

```
agents/
├── context/scene_summarizer.toml
├── pretranslation/idiom_labeler.toml
├── translate/direct_translator.toml
├── qa/style_guide_critic.toml
└── edit/basic_editor.toml
```

A profile contains:

```toml
[meta]
name = "direct_translator"
phase = "translate"
output_schema = "TranslationResultList"

[prompts.agent]
content = "..."         # Agent-layer system prompt

[prompts.user_template]
content = "..."         # User prompt template with {{variables}}

[tools]
allowed = ["get_game_info"]
required = ["get_game_info"]

[model_hints]
recommended = ["gpt-5.2", "claude-4.5-sonnet"]
min_context_tokens = 16384
```

Profiles are loaded and validated by `load_agent_profile()` in `rentl_agents.profiles.loader`. The `AgentProfileConfig` schema in `rentl_schemas.agents` defines the full structure.

### Three-Layer Prompt System

Prompts are composed from three layers, each stored as TOML:

| Layer | File | Scope |
|---|---|---|
| Root | `prompts/root.toml` | Project-wide framing (game name, synopsis) |
| Phase | `prompts/phases/{phase}.toml` | Phase-level instructions (source/target language) |
| Agent | `agents/{phase}/{name}.toml` | Agent-specific instructions and user template |

The `PromptComposer` class in `rentl_agents.layers` joins the three system layers with `"\n\n---\n\n"` separators into a single system prompt. The user prompt comes from the agent's `[prompts.user_template]`.

Template variables use `{{variable_name}}` syntax. Each layer has a defined set of allowed variables (enforced at load time). Variables from later layers override earlier ones via `TemplateContext` in `rentl_agents.templates`.

### pydantic-ai Integration

The `ProfileAgent` class in `rentl_agents.runtime` bridges profiles to LLM calls:

1. Composes system + user prompts via `PromptComposer`
2. Detects provider capabilities via `detect_provider()` (OpenRouter, OpenAI, local, or generic)
3. Constructs a `pydantic_ai.Agent` with the profile's `output_schema` as the structured output type
4. Runs the agent with `usage_limits` and `model_settings` from config
5. Returns the validated output (e.g., `TranslationResultList`)

### Phase-Specific Wrapper Agents

Each phase has a wrapper class in `rentl_agents.wiring` that handles chunking, alignment checking, and result merging:

| Wrapper Class | Phase | Output Type |
|---|---|---|
| `ContextSceneSummarizerAgent` | context | `SceneSummary` |
| `PretranslationIdiomLabelerAgent` | pretranslation | `IdiomAnnotationList` |
| `TranslateDirectTranslatorAgent` | translate | `TranslationResultList` |
| `QaStyleGuideCriticAgent` | qa | `StyleGuideReviewList` |
| `EditBasicEditorAgent` | edit | `TranslationResultLine` |

The top-level entry point is `build_agent_pools()` in `rentl_agents.wiring`, which discovers profiles, creates wrapper agents, and returns an `AgentPoolBundle` for the orchestrator.

---

## Data Flow

The core data transformation is `SourceLine` → `TranslatedLine`, defined in `rentl_schemas.io`:

```
CSV/JSONL/TXT  ──ingest──▶  SourceLine
                                │
                    context:    │  SceneSummary
                    pretrans:   │  IdiomAnnotationList
                                │
                   translate ──▶  TranslatedLine
                                │
                         qa:    │  QaIssue[]
                                │
                       edit  ──▶  TranslatedLine (revised)
                                │
                     export  ──▶  CSV/JSONL/TXT
```

`SourceLine` fields: `line_id`, `scene_id`, `speaker`, `text`, `metadata`, `route_id`, `source_columns`.

`TranslatedLine` extends the same structure with `source_text` (the original text for reference).

Phase outputs accumulate in `PipelineRunContext`: `context_output`, `pretranslation_output`, `translate_outputs` (per language), `qa_outputs` (per language), `edit_outputs` (per language).

---

## Port/Adapter Pattern

Core business logic defines protocol interfaces ("ports") in `rentl_core.ports`. Concrete implementations ("adapters") live in `rentl-io` and `rentl-agents`.

### Ports (in `rentl_core.ports`)

| Port | Module | Purpose |
|---|---|---|
| `IngestAdapterProtocol` | `ports.ingest` | Read source files into `SourceLine` objects |
| `ExportAdapterProtocol` | `ports.export` | Write `TranslatedLine` objects to output files |
| `PhaseAgentProtocol` | `ports.orchestrator` | Execute an agent for a pipeline phase |
| `LogSinkProtocol` | `ports.orchestrator` | Emit structured JSONL log entries |
| `ProgressSinkProtocol` | `ports.orchestrator` | Emit `ProgressUpdate` events |
| `RunStateStoreProtocol` | `ports.storage` | Persist and load run state |
| `ArtifactStoreProtocol` | `ports.storage` | Persist and load phase artifacts |
| `LogStoreProtocol` | `ports.storage` | Persist and load log entries |
| `LlmRuntimeProtocol` | `ports.llm` | Execute ad-hoc LLM prompts |

### Adapters

**Ingest** (`rentl_io.ingest`): `CsvIngestAdapter`, `JsonlIngestAdapter`, `TxtIngestAdapter`. Selected by `get_ingest_adapter(file_format)`.

**Export** (`rentl_io.export`): `CsvExportAdapter`, `JsonlExportAdapter`, `TxtExportAdapter`. Selected by `get_export_adapter(file_format)`.

**Storage** (`rentl_io.storage`): `FileSystemRunStateStore`, `FileSystemArtifactStore`, `FileSystemLogStore`. All filesystem-based, using `asyncio.to_thread` for non-blocking I/O.

**Logging** (`rentl_io.storage.log_sink`): `StorageLogSink`, `ConsoleLogSink`, `NoopLogSink`, `CompositeLogSink`, `RedactingLogSink`. Composed via `build_log_sink()`.

**Progress** (`rentl_io.storage.progress_sink`): `FileSystemProgressSink`, `InMemoryProgressSink`, `CompositeProgressSink`.

**LLM** (`rentl_llm`): `OpenAICompatibleRuntime` — works with any OpenAI-compatible endpoint (OpenRouter, OpenAI, local models).

---

## Storage Model

Run data is split across two filesystem roots within the workspace:

**`.rentl/`** — run state and artifacts (managed by `rentl-io` storage adapters):

```
.rentl/
├── run_state/
│   ├── runs/{run_id}.json         # Full run state (RunState)
│   └── index/{run_id}.json        # Run index entry
└── artifacts/
    └── {run_id}/
        ├── artifact-{id}.json     # Phase output (single object)
        ├── artifact-{id}.jsonl    # Phase output (line-delimited)
        └── index.jsonl            # Artifact index
```

**`project.paths.logs_dir`** (default `./logs`) — logs, progress, and reports:

```
{logs_dir}/
├── {run_id}.jsonl                 # Structured log entries
├── progress/{run_id}.jsonl        # ProgressUpdate stream
└── reports/{run_id}.json          # Post-run summary report
```

The `FileSystemProgressSink` appends `ProgressUpdate` JSONL records to the progress file. The CLI's `status --watch` command tail-reads this file for live updates.

Artifacts are written after each phase completes. The `RedactingLogSink` and `_RedactingArtifactStore` scrub API keys from all persisted data using the `Redactor` class.

---

## CLI

The CLI (`services/rentl-cli/`) is a thin adapter over `rentl-core`. Entry point: `rentl.main:app` (Typer).

Key commands:

| Command | What it does |
|---|---|
| `rentl init` | Interactive project setup (generates `rentl.toml` + `.env`) |
| `rentl doctor` | Validates configuration and environment |
| `rentl run-pipeline` | Runs all enabled phases end-to-end |
| `rentl run-phase` | Runs a single phase with prerequisites |
| `rentl status` | Shows run progress (supports `--watch` for live updates) |
| `rentl export` | Writes translations to output files |
| `rentl explain` | Describes pipeline phases |
| `rentl validate-connection` | Tests LLM endpoint connectivity |
| `rentl benchmark download` | Downloads benchmark datasets |
| `rentl benchmark compare` | Runs pairwise quality evaluation |

The CLI assembles all dependencies — config loading, storage bundle, agent pools, ingest/export adapters — then delegates to `PipelineOrchestrator.run_plan()`. Output is dual-mode: Rich panels for TTY, JSON for piped output.

---

## BYOK (Bring Your Own Key)

rentl supports any OpenAI-compatible LLM endpoint. Configuration in `rentl.toml` uses either a single `[endpoint]` table or a multi-endpoint `[endpoints]` table with a `default` reference and `[[endpoints.endpoints]]` entries:

```toml
# Single endpoint
[endpoint]
provider_name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "RENTL_LOCAL_API_KEY"

# Multi-endpoint (use instead of [endpoint], not alongside it)
# [endpoints]
# default = "OpenRouter"
# [[endpoints.endpoints]]
# provider_name = "OpenRouter"
# base_url = "https://openrouter.ai/api/v1"
# api_key_env = "RENTL_LOCAL_API_KEY"
```

`detect_provider()` in `rentl_agents.providers` identifies the provider from the base URL and returns a `ProviderCapabilities` object describing supported features (tool calling, tool choice, etc.), allowing rentl to adapt without provider-specific code paths.

---

## Deterministic QA

In addition to LLM-powered QA agents, the orchestrator runs deterministic checks via `DeterministicQaRunner` in `rentl_core.qa.runner`. These are rule-based checks (e.g., formatting, length limits) configured per-project. Results merge into the same `QaPhaseOutput` as agent-produced issues.
