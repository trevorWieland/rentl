# rentl

A multi-agent, context-aware translation pipeline for visual novels—turning raw scene text and metadata into high-quality, consistent JP→EN localizations. Phases are driven by deterministic pipelines (no LLM top-level coordinators), with LangChain subagents, provenance-aware tools, and human-in-the-loop controls.

---

## Overview

rentl mirrors how human teams localize VNs today with distinct phases:

1. **Context Builder (v1.0)** – operates entirely in the source language to enrich metadata: scene summaries, character/location bios, glossary entries, and route context.
2. **Translator (v1.0)** – consumes the curated context via read-only tools and produces aligned JP→EN translations.
3. **Editor (v1.0)** – reviews source/target pairs, enforces style guides, and flags issues for retranslation or human review.

Each phase is orchestrated by code-driven pipelines that schedule LangChain subagents (scene detailers, translators, QA checkers). Human-in-the-loop is handled with LangChain HITL middleware and provenance-aware tools. A modern TUI (Textual) is planned for non-technical users, alongside the CLI. Git serves as the version control mechanism for all metadata and translations.

### What rentl Does

- **Context-first translation**: Agents use character bios, glossaries, style guides, and scene summaries to produce consistent translations
- **Human-in-the-loop controls**: Provenance tracking protects human-authored data while allowing agents to fill gaps and refine their own work
- **Aligned corpus output**: Produces `(source line, translation, metadata)` pairs in JSONL format for easy review and export
- **One repo per game**: Each translation project is a git-tracked repository with its own metadata, scenes, and configuration

### What rentl Does NOT Do (Non-Goals)

- **No text extraction**: rentl assumes text is already extracted and cleaned from the game engine
- **No live/OCR translation**: No hooking into running games or overlaying translations in real-time
- **No patch building**: rentl outputs aligned translation files; external tools handle patch generation for specific engines
- **No "rewrite the story" localization**: Focus is on faithful translation with light localization, not creative rewriting

---

## Installation

**Requirements:**

- Python 3.13
- [uv](https://github.com/astral-sh/uv) for dependency/runtime management
- Access to an OpenAI-compatible chat endpoint (OpenAI, LM Studio, Ollama, etc.)

**Setup:**

```bash
git clone https://github.com/anthropics/rentl.git
cd rentl
uv sync
cp template.env .env  # fill in OPENAI_URL, OPENAI_API_KEY, LLM_MODEL
```

**Environment Variables** (`.env`):

```bash
# Primary LLM (for agentic reasoning and orchestration)
OPENAI_URL=http://localhost:1234/v1        # or https://api.openai.com/v1
OPENAI_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o                           # or local model name

# Machine Translation (MTL) backend (optional, for specialized translation)
MTL_URL=http://localhost:1234/v1           # OpenAI-compatible endpoint
MTL_API_KEY=your-api-key-here
MTL_MODEL=sugoi-14b-ultra                  # Specialized JP→EN model

# Optional services
TAVILY_API_KEY=optional-for-web-search
LANGSMITH_API_KEY=optional-for-observability
```

### Suggested Models

| Purpose              | Model                                      | Notes                          |
|----------------------|--------------------------------------------|--------------------------------|
| Agentic reasoning    | `gpt-oss:20b` (LM Studio)                  | Local, tested                  |
| JP→EN translation    | `sugoi-14b-ultra` (Sugoi-14B-Ultra-GGUF)   | Via MTL backend (v1.0)         |

---

## Basic Usage

**Note**: Full Copier template and project scaffolding (`rentl init`) will be available later in v1.0. For now, use `examples/tiny_vn` or a temp baseline.

```bash
# Validate metadata + scene files
uv run python -m rentl_cli.main validate --project-path examples/tiny_vn

# Context builder: detail all scenes (generates summary, tags, characters, locations)
# Context builder: detail scenes (pipeline mode)
uv run python -m rentl_cli.main context --project-path examples/tiny_vn
```

**Available flags:**
- `--project-path PATH`: Path to game project (default: current directory; pass `examples/tiny_vn` for the included sample)
- `--overwrite`: Allow agents to overwrite existing data
- `--verbose`: Enable detailed logging
- `--thread-id`: Resume a HITL-interrupted run (persisted checkpoints under `.rentl/checkpoints.db`)

Pipelines include bounded concurrency, retry/backoff for transient errors, and scene-level progress callbacks. In `--verbose` mode, the CLI prints start/done/error events per entity and summarizes any errors at the end of a run.

**In progress for v1.0**:
- `rentl init` - Initialize a new game project from Copier template
- `rentl context` - Run Context Builder phase (all detailer subagents)
- `rentl translate` - Run Translator phase
- `rentl edit` - Run Editor phase (QA checks + report output)
- Persistent HITL/resume via SQLite checkpointer (`.rentl/checkpoints.db` by default; override with `RENTL_CHECKPOINT_DB`)

---

## Architecture

rentl is a **Python 3.13 monorepo** using:

- **uv** for workspace and dependency management
- **LangChain** for subagents + HITL middleware (pipelines drive orchestration; no LLM coordinators)
- **Pydantic** for data models and configuration
- **orjson** for fast JSONL I/O
- **anyio** for async-first execution
- **Typer** for the CLI
- **ruff** and **ty** for linting and type checking
- **pytest** for testing

### Project Structure

```
rentl/
  apps/
    cli/              # Typer-based CLI (rentl-cli)
    server/           # (Future) Web UI and REST API
  libs/
    core/             # Data models, I/O, config (rentl-core)
    agents/           # Subagents, tools, LLM backends (rentl-agents)
    pipelines/        # Orchestration flows (rentl-pipelines)
    templates/        # Copier template for per-game repos (rentl-templates)
  examples/
    tiny_vn/          # Example project with sample scenes
```

### Provenance Tracking and HITL

rentl uses **provenance tracking** (`*_origin` fields) to record whether each metadata field was last set by a human or an agent. This enables intelligent human-in-the-loop (HITL) approval:

- Agents can freely fill in empty/missing fields
- Agents can refine their own prior work without approval
- Human-authored data is protected—agents must request approval to modify it

**Tool approval policies:**
- **read_* tools**: Never require approval
- **add_* tools**: May require approval based on policy (`permissive` or `strict`)
- **update_* tools**: Check provenance—approve only if overwriting human data
- **delete_* tools**: Check provenance—approve if any field was human-authored

See [SCHEMAS.md](SCHEMAS.md) for complete provenance documentation.

---

## Agents (v1.0)

| Agent            | Responsibilities                                                                  | Status              |
|------------------|-----------------------------------------------------------------------------------|---------------------|
| Context Builder  | Scene, character, location, glossary, and route metadata enrichment               | **Implemented**     |
| Translator       | Consume context, produce aligned JP→EN translations                               | **Implemented**     |
| Editor           | QA checks (style, consistency, translation quality), flag issues for retranslation | **Implemented**     |

---

## Subagents

### Context Builder Subagents (v1.0)

| Subagent            | Purpose                                                                                  | Status              |
|---------------------|------------------------------------------------------------------------------------------|---------------------|
| `scene_detailer`    | Generates scene summaries, tags, primary characters, and locations                       | **Implemented**     |
| `character_detailer`| Expands character bios, pronoun guidance, speech pattern notes                           | **Implemented**     |
| `location_detailer` | Captures location descriptions, mood cues, atmospheric details                           | **Implemented**     |
| `glossary_detailer` | Proposes new glossary entries or updates via HITL approval                               | **Implemented**     |
| `route_detailer`    | Enriches route metadata (synopsis, primary characters) with human supervision            | **Implemented**     |

### Translator Subagents (v1.0)

| Subagent           | Purpose                                                                                           | Status          |
|--------------------|---------------------------------------------------------------------------------------------------|-----------------|
| `scene_translator` | Dual approach: direct context-aware translation OR specialized MTL model calls (e.g., Sugoi-14B)  | **Implemented** |

### Editor Subagents (v1.0)

| Subagent                      | Purpose                                                                      | Status          |
|-------------------------------|------------------------------------------------------------------------------|-----------------|
| `scene_style_checker`         | Enforces style guide (tone, honorific policies, formatting)                  | **Implemented** |
| `scene_consistency_checker`   | Cross-scene review for terminology, pronouns, character names                | **Implemented** |
| `scene_translation_reviewer`  | Reviews translation quality, flags lines for retranslation                   | **Implemented** |

---

## Tools (v1.0)

| Tool                      | Description                                                              | Agents/Subagents        | Status            |
|---------------------------|--------------------------------------------------------------------------|-------------------------|-------------------|
| `read_scene_overview`     | Scene metadata + transcript + stored summary (hidden when overwriting)   | Context, Translator     | **Implemented**   |
| `list_context_docs`       | Lists documents under `metadata/context_docs/`                           | All agents              | **Implemented**   |
| `read_context_doc`        | Returns contents of a context document                                   | All agents              | **Implemented**   |
| `write_scene_summary`     | Writes scene summary (single-use; overwrite requires flag)               | Context                 | **Implemented**   |
| `write_scene_tags`        | Writes scene tags (single-use; overwrite requires flag)                  | Context                 | **Implemented**   |
| `write_primary_characters`| Writes primary character IDs (single-use; overwrite requires flag)       | Context                 | **Implemented**   |
| `write_scene_locations`   | Writes location IDs (single-use; overwrite requires flag)                | Context                 | **Implemented**   |
| `read_character`          | Returns character metadata (names, pronouns, bio)                        | Context, Translator     | **Implemented**   |
| `update_character`        | Updates character fields with HITL approval                              | Context                 | **Implemented**   |
| `read_location`           | Returns location metadata (names, description)                           | Context, Translator     | **Implemented**   |
| `update_location`         | Updates location fields with HITL approval                               | Context                 | **Implemented**   |
| `read_glossary`           | Searches glossary entries by term                                        | Translator, Editor      | **Implemented**   |
| `add_glossary_entry`      | Proposes new glossary entry with HITL approval                           | Context                 | **Implemented**   |
| `update_glossary_entry`   | Updates existing glossary entry with HITL approval                       | Context                 | **Implemented**   |
| `read_route`              | Returns route metadata (synopsis, scene ordering, characters)            | Context                 | **Implemented**   |
| `update_route`            | Updates route fields with HITL approval                                  | Context                 | **Implemented**   |
| `mtl_translate`           | Calls specialized MTL backend for translation (e.g., Sugoi-14B)          | Translator              | **Implemented**   |
| `write_translation`       | Writes translation for a line (provenance tracked)                       | Translator              | **Implemented**   |
| `record_style_check`      | Records style guide compliance check results                             | Editor                  | **Implemented**   |
| `record_consistency_check`| Records terminology/pronoun consistency check results                    | Editor                  | **Implemented**   |
| `record_quality_check`    | Records translation quality review results                               | Editor                  | **Implemented**   |

---

## Testing & Development

Run the repo-standard checks before committing:

```bash
make fix   # format + lint autofix
make check # format check, lint, type check, and pytest (includes tiny_vn smoke)
```

Integration coverage includes pipeline retry handling and a mocked tiny_vn end-to-end smoke (context → translate → edit) to ensure the phases wire together without real LLM calls.

## Roadmap

### v1.0 – Core Translation Pipeline (Current Target)

**Goal**: Translate a complete visual novel from start to finish using the three-phase workflow.

**Features**:
- ✅ Data models with provenance tracking (`*_origin` fields)
- ✅ Async loaders for all metadata formats
- ✅ Project validation (referential integrity checks)
- 🚧 Copier template for per-game project scaffolding
- ✅ All Context Builder subagents (scene, character, location, glossary, route detailers)
- ✅ Translator subagent with context-aware translation
- ✅ Editor subagents (style, consistency, quality checks)
- 🚧 HITL approval workflow with provenance-based gating
- 🚧 CLI commands: `init`, `context`, `translate`, `edit`, `validate`
- 🚧 Complete tool suite for all subagents
- 🚧 Example project (`examples/tiny_vn`) with full translations

**Deferred to v1.1+**: Pretranslator agent, items/bgm metadata, advanced search tools.

### v1.1 – Enhanced Detection & Observability

**Focus**: Pretranslator + richer context detection + agent debugging tools

**Features** (priorities based on v1.0 usage):
- **Pretranslator agent** with subagents:
  - `idiom_detector`: Identifies idioms and cultural references
  - `accent_profiler`: Notes accent, dialect, speech quirks
  - `grammar_annotator`: Captures tricky grammar patterns
- **Tavily web search integration**: Reference and cultural context detection during context building
- **LangSmith integration**: Agent trace visualization and debugging dashboards
- **Enhanced search** (Meilisearch or similar): Fast vector/keyword search over context docs, glossary, and metadata
- **CLI command**: `rentl pretranslate` for Pretranslator phase
- Quality-of-life improvements based on real-world usage

### v1.2 – Export Formats

**Focus**: Get translations into other tools and workflows

**Features**:
- Translator++ compatible export adapter
- Additional export formats (CSV, TMX, XLIFF, etc.)
- Batch processing improvements
- Performance optimizations

### v1.3 – Web UI

**Focus**: Interactive review and approval interface

**Features**:
- Web-based translation review
- HITL approval dashboard with side-by-side comparison
- Visual context browsing (characters, locations, glossary)
- Real-time collaboration tools

### v1.4 – RPGMaker Support

**Focus**: Expand to RPG and gameplay-heavy visual novels

**Features**:
- `items.jsonl` metadata schema (inventory, spells, named objects)
- `bgm.jsonl` metadata schema (music cues and descriptions)
- RPGMaker-specific export formats
- Gameplay text handling (menus, UI, skills, etc.)

### v2.0 – Ecosystem & Extensibility

**Focus**: Community contributions and multi-language support

**Features**:
- Plugin system for custom subagents and tools
- Additional language pairs beyond JP→EN
- Community-contributed subagent library
- Advanced observability and analytics

---

## Contributing

Contributions are welcome! Areas of interest:

- **New subagents**: Specialized detectors, formatters, or QA checks
- **Export formats**: Adapters for translation tools and game engines
- **Metadata schemas**: Extensions for specific game genres (RPG, ADV, etc.)
- **Documentation**: Tutorials, guides, and real-world case studies

For now, extending rentl involves forking and modifying pipelines/subagents directly. A plugin system is planned for v2.0.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Resources

- **[SCHEMAS.md](SCHEMAS.md)**: Complete data format documentation with provenance tracking
- **[AGENTS.md](AGENTS.md)**: Guidelines for AI coding agents working on rentl
- **[Examples](examples/tiny_vn)**: Sample project structure and data

---

## Acknowledgments

Built with:
- [LangChain](https://github.com/langchain-ai/langchain) for subagents, HITL middleware, and LLM integration
- [Pydantic](https://github.com/pydantic/pydantic) for data validation
- [uv](https://github.com/astral-sh/uv) for Python project management
