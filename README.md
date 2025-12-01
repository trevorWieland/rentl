# rentl

A multi-agent, context-aware translation pipeline for visual novels—turning raw scene text and metadata into high-quality, consistent localizations for any source→target language pair. Phases are driven by deterministic pipelines (no LLM top-level coordinators), with LangChain subagents, provenance-aware tools, and human-in-the-loop controls.

---

## Overview

rentl mirrors how human teams localize VNs today with distinct phases:

1. **Context Builder (v1.0)** – operates entirely in the source language to enrich metadata: scene summaries, character/location bios, glossary entries, and route context.
2. **Translator (v1.0)** – consumes the curated context via read-only tools and produces aligned translations in the configured target language.
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

# Machine Translation (MTL) backend (optional, for specialized translation; current model is JP→EN only)
MTL_URL=http://localhost:1234/v1           # OpenAI-compatible endpoint
MTL_API_KEY=your-api-key-here
MTL_MODEL=sugoi-14b-ultra                  # Specialized JP→EN model (optional)

# Optional services
TAVILY_API_KEY=optional-for-web-search
LANGSMITH_API_KEY=optional-for-observability
```

### Suggested Models

| Purpose              | Model                                      | Notes                                   |
|----------------------|--------------------------------------------|-----------------------------------------|
| Agentic reasoning    | `gpt-oss:20b` (LM Studio)                  | Local, tested                           |
| Example JP→EN MTL    | `sugoi-14b-ultra` (Sugoi-14B-Ultra-GGUF)   | Optional MTL backend (currently JP→EN)  |

---

## Basic Usage

**Note**: Full Copier template and project scaffolding (`rentl init`) will be available later in v1.0. For now, use `examples/tiny_vn` or a temp baseline.

```bash
# Validate metadata + scene files
uv run python -m rentl_cli.main validate --project-path examples/tiny_vn

# Context builder: detail scenes (summary, tags, characters, locations, glossary)
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
| Translator       | Consume context, produce aligned translations in the configured target language   | **Implemented**     |
| Editor           | QA checks (style, consistency, translation quality), flag issues for retranslation | **Implemented**     |

---

## Subagents

### Context Builder Subagents (v1.0)

| Subagent                            | Purpose                                                                                  | Status              |
|-------------------------------------|------------------------------------------------------------------------------------------|---------------------|
| `scene_summary_detailer`            | Writes scene summary (source language, concise, single-use)                             | **Implemented**     |
| `scene_tag_detailer`                | Assigns scene tags                                                                       | **Implemented**     |
| `scene_primary_character_detailer`  | Sets primary character IDs for a scene                                                   | **Implemented**     |
| `scene_location_detailer`           | Sets scene location IDs and enriches location metadata                                   | **Implemented**     |
| `scene_glossary_detailer`           | Adds/updates glossary entries discovered in a scene                                      | **Implemented**     |
| `meta_character_curator`            | Polishes/deduplicates character metadata                                                 | **Implemented**     |
| `meta_location_curator`             | Polishes/deduplicates location metadata                                                  | **Implemented**     |
| `meta_glossary_curator`             | Polishes/merges glossary entries                                                         | **Implemented**     |
| `route_outline_builder`             | Writes route synopsis and primary characters                                             | **Implemented**     |

### Translator Subagents (v1.0)

| Subagent           | Purpose                                                                                           | Status          |
|--------------------|---------------------------------------------------------------------------------------------------|-----------------|
| `scene_translator` | Dual approach: direct context-aware translation OR specialized MTL model calls (e.g., Sugoi-14B)  | **Implemented** |

### Editor Subagents (v1.0)

| Subagent                      | Purpose                                                                      | Status          |
|-------------------------------|------------------------------------------------------------------------------|-----------------|
| `scene_style_checker`         | Enforces style guide (tone, honorific policies, formatting)                  | **Implemented** |
| `route_consistency_checker`   | Records per-line consistency checks on translated scenes                     | **Implemented** |
| `scene_translation_reviewer`  | Reviews translation quality, flags lines for retranslation                   | **Implemented** |

---

## Tools (v1.0)

| Tool                            | Description                                                              | Agents/Subagents        | Status            |
|---------------------------------|--------------------------------------------------------------------------|-------------------------|-------------------|
| `scene_read_overview`           | Scene metadata + transcript + stored summary (hidden when overwriting)   | Context, Translator     | **Implemented**   |
| `scene_read_metadata`           | Scene metadata without transcript                                        | Context                 | **Implemented**   |
| `scene_read_redacted`           | Scene metadata + transcript with summary redacted                        | Context                 | **Implemented**   |
| `scene_update_summary`          | Writes scene summary (single-use guard)                                  | Context                 | **Implemented**   |
| `scene_update_tags`             | Writes scene tags (single-use guard)                                     | Context                 | **Implemented**   |
| `scene_update_primary_characters`| Writes primary character IDs (single-use guard)                         | Context                 | **Implemented**   |
| `scene_update_locations`        | Writes location IDs (single-use guard)                                   | Context                 | **Implemented**   |
| `character_read_entry`          | Returns character metadata (names, pronouns, notes)                      | Context, Translator     | **Implemented**   |
| `character_create_entry`        | Creates a character entry                                                | Context                 | **Implemented**   |
| `character_update_name_tgt`     | Updates character target name with HITL/provenance                       | Context                 | **Implemented**   |
| `character_update_pronouns`     | Updates character pronouns with HITL/provenance                          | Context                 | **Implemented**   |
| `character_update_notes`        | Updates character notes with HITL/provenance                             | Context                 | **Implemented**   |
| `character_delete_entry`        | Deletes a character (approval required for human-authored fields)        | Context                 | **Implemented**   |
| `location_read_entry`           | Returns location metadata                                                | Context, Translator     | **Implemented**   |
| `location_create_entry`         | Creates a location entry                                                 | Context                 | **Implemented**   |
| `location_update_name_tgt`      | Updates location target name with HITL/provenance                        | Context                 | **Implemented**   |
| `location_update_description`   | Updates location description with HITL/provenance                        | Context                 | **Implemented**   |
| `location_delete_entry`         | Deletes a location (approval required for human-authored fields)         | Context                 | **Implemented**   |
| `glossary_search_term`          | Searches glossary entries by source term                                 | Context, Translator, Editor | **Implemented** |
| `glossary_read_entry`           | Reads a specific glossary entry                                           | Context, Translator, Editor | **Implemented** |
| `glossary_create_entry`         | Creates a glossary entry                                                  | Context                 | **Implemented**   |
| `glossary_update_entry`         | Updates a glossary entry                                                  | Context                 | **Implemented**   |
| `glossary_merge_entries`        | Merges glossary entries                                                   | Context                 | **Implemented**   |
| `glossary_delete_entry`         | Deletes a glossary entry (approval required for human-authored fields)   | Context                 | **Implemented**   |
| `route_read_entry`              | Returns route metadata                                                    | Context                 | **Implemented**   |
| `route_create_entry`            | Creates a route entry                                                     | Context                 | **Implemented**   |
| `route_update_synopsis`         | Updates route synopsis with HITL/provenance                               | Context                 | **Implemented**   |
| `route_update_primary_characters`| Updates route primary characters with HITL/provenance                    | Context                 | **Implemented**   |
| `route_delete_entry`            | Deletes a route (approval required for human-authored fields)             | Context                 | **Implemented**   |
| `styleguide_read_full`          | Reads the project style guide                                             | Translator, Editor      | **Implemented**   |
| `ui_read_settings`              | Reads UI constraints                                                      | Translator, Editor      | **Implemented**   |
| `translation_check_mtl_available`| Checks MTL backend availability                                          | Translator              | **Implemented**   |
| `translation_create_mtl_suggestion`| Calls specialized MTL backend for translation                           | Translator              | **Implemented**   |
| `translation_create_line`       | Writes translation for a line (provenance tracked)                        | Translator              | **Implemented**   |
| `translation_update_line`       | Overwrites translation for a line (provenance tracked)                    | Translator              | **Implemented**   |
| `translation_read_scene`        | Reads translated lines for a scene                                        | Editor                  | **Implemented**   |
| `translation_create_style_check`| Records style guide compliance check results                              | Editor                  | **Implemented**   |
| `translation_create_consistency_check`| Records terminology/pronoun consistency check results               | Editor                  | **Implemented**   |
| `translation_create_review_check`| Records translation quality review results                               | Editor                  | **Implemented**   |
| `contextdoc_list_all`           | Lists documents under `metadata/context_docs/`                            | All agents              | **Implemented**   |
| `contextdoc_read_doc`           | Returns contents of a context document                                    | All agents              | **Implemented**   |
| `context_read_status`           | Reports pipeline status counters                                          | Pipelines               | **Implemented**   |

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
- ✅ HITL approval workflow with provenance-based gating (CLI resume/status UX still in progress)
- 🚧 CLI commands: `init`, `context`, `translate`, `edit`, `validate`
- 🚧 Complete tool suite for all subagents

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
- Additional MTL models/language-specific shortcuts (current MTL example is JP→EN; core pipeline is language-agnostic)
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
