# rentl – Design Document (Draft)

> **Tagline**: A multi-agent, context-aware translation pipeline for visual novels—turning raw scene text and metadata into high-quality, consistent localizations.

---

## 1. Goals & Non-Goals

### 1.1 Goals

- Provide an **open-source**, **extensible** translation framework for visual novels (initially JP → EN) built around:

  - **Context-aware, multi-agent translation** (scene-level and game-level).
  - **Strong project structure** that plays well with git and iterative workflows.
  - **Configurable style & localization rules** (glossaries, character sheets, honorific handling, etc.).

- Operate on **pre-extracted, cleaned text** + metadata and produce:

  - A **pairwise aligned corpus**: `(source line, translated line, metadata)` that references stable line IDs.
  - Additional annotations (idioms, references, etc.) as metadata.

- Be **LLM-backend flexible**:

  - Support any OpenAI-compatible endpoint (OpenAI, LM Studio, Ollama, etc.) via LangChain’s `ChatOpenAI`.
  - Allow optional integrations such as Tavily (web search) and LangSmith (observability).

- Provide a **CLI + project template** so end users:

  - Create one repo per game.
  - Configure translation rules and metadata.
  - Run pipelines without needing to write code.

### 1.2 Non-Goals (for the rentl core)

- **No text extraction**:

  - rentl assumes text and scenes are already extracted and cleaned.

- **No live/OCR translation**:

  - No hooking into running games or overlaying translations.

- **No patch building**:

  - rentl outputs aligned corpora that _other tools_ (e.g., patch builders, fansub toolchains, Translator++ exports) can consume.

- **No “rewrite the game” localization**:

  - rentl focuses on translation and light localization within the intent and tone of the original; it is not a rewriting tool.

---

## 2. High-Level Architecture

rentl is a **Python 3.13 monorepo** using:

- **uv** for dependency and workspace management.
- **ruff** and **ty** for linting and type checking.
- **pytest** for testing.
- **pydantic** for configuration and data models.
- **async-first** design for orchestration.
- **orjson** for fast JSONL I/O.
- **typer** for the CLI.
- **langchain / deepagents** as the core multi-agent orchestration layer, with DeepAgents coordinating specialized subagents plus shared middleware (Todo list, filesystem, subagent spawning).
- **LangChain’s ChatOpenAI** for LLMs (OpenAI-compatible, including LM Studio and Ollama).
- **Tavily** as the first web-search provider for subagents (optional).
- **LangSmith** as an optional observability / analysis layer.

### 2.1 Conceptual Overview

At a high level:

1. **Project Template**
   Users create a game-specific repo using a **Copier** template. The project contains:

   - Game metadata (`game.json`, `characters.jsonl`, `glossary.jsonl`, `locations.jsonl`, etc.) plus style guide/context docs.
   - Input scenes (JSONL).
   - Output directories for translated corpora and reports.
   - A project config file that defines languages, LLM backends, and pipeline settings.

2. **CLI Interface**
   The `rentl` CLI (Typer-based) is used to:

   - Initialize a new project from the Copier template.
   - Run translation pipelines on the project (e.g., scene-level MVP, later full-game pipelines).

3. **Core Library**
   The core library defines:

   - Data models for lines and scenes.
   - Config models for projects, LLM backends, and metadata.
   - I/O utilities for reading/writing JSONL and other formats.

4. **Subagent Layer (deepagents)**
   Specialized DeepAgents subagents implemented on top of LangChain + LangGraph:

   - Scene summarization.
   - Idiom and reference detection (with optional Tavily web search).
   - Scene translation specialists (optionally on multiple backends).
   - Synthesis subagents that refine and select among candidate translations.
   - Style and consistency checkers.
   - Formatting audits (line length, unsupported characters).
   - Glossary / metadata curator that proposes new entries via HITL tool calls.

5. **Pipelines**
   Pipelines orchestrate DeepAgents-driven subagent workflows across scenes:

   - v1 focuses on **scene-level pipelines** that operate on one scene at a time, using multi-step subagent flows.
   - Longer-term: game-level or route-level pipelines that re-run subagents over collections of scenes, in multiple passes.

---

## 3. Monorepo Structure

The monorepo is structured as a uv workspace with the following layout:

```text
rentl/
  pyproject.toml              # uv workspace root, dev tooling, shared config
  uv.lock

  apps/
    cli/
      pyproject.toml          # project = "rentl-cli"
      rentl_cli/
        __init__.py
        main.py               # Typer app entrypoint
        commands/
          init.py             # `rentl init`
          run.py              # `rentl run`
          inspect.py          # `rentl inspect` (future)
      tests/

    server/                   # (future) for web UI / REST API
      pyproject.toml
      rentl_server/
        ...
      tests/

  libs/
    core/
      pyproject.toml          # project = "rentl-core"
      rentl_core/
        __init__.py
        config/
          settings.py         # general settings (env-based)
          project.py          # per-game project config models
        model/
          line.py             # Line model, minimal scene info
          scene.py            # Scene model (collection of Lines)
        io/
          loader.py           # read scenes JSONL -> models
          writer.py           # write aligned corpora, reports
        util/
          logging.py
          errors.py
      tests/

    agents/
      pyproject.toml          # project = "rentl-agents"
      rentl_agents/
        __init__.py
        backends/
          base.py             # abstract “LLM backend” interface
          openai_like.py      # LangChain ChatOpenAI wrapper
          tavily.py           # Tavily search client wrapper
          langsmith.py        # optional integration helpers
        graph/
          engine.py           # deepagents create_deep_agent setup, middleware wiring, subagent registry helpers
        subagents/
          summarize_scene.py
          summarize_route.py      # (may be used by game-level pipelines)
          summarize_game.py       # (future)
          detect_puns.py
          detect_references.py
          translate_scene.py
          synthesize_translation.py
          consistency_checks.py
          style_checks.py
          formatting_checks.py
      tests/

    pipelines/
      pyproject.toml          # project = "rentl-pipelines"
      rentl_pipelines/
        __init__.py
        flows/
          scene_mvp.py        # v1 pipeline: scene-focused translation
          full_game.py        # (future) orchestrates scenes/routes
        runner.py             # APIs to run pipelines on project paths
      tests/

    templates/
      pyproject.toml          # project = "rentl-templates"
      rentl_templates/
        __init__.py
        copier/
          copier.yml          # Copier configuration
          {{project_slug}}/   # game project template
            rentl.project.toml
            metadata/
              game.json
              characters.jsonl
              glossary.jsonl
              locations.jsonl
              items.jsonl
              routes.jsonl
              scenes.jsonl
              bgm.jsonl
              style_guide.md
              context_docs/   # prequels, manuals, etc. referenced by subagents for context
            input/
              scenes/         # *.jsonl
            output/
              translations/
              reports/
      tests/

  examples/
    tiny_vn/
      ...                     # minimal working project example

  .github/
    workflows/
      ci.yml                  # ruff, ty, pytest, minimal tests

  LICENSE                     # MIT
  README.md
```

---

## 4. Data Model & File Formats

### 4.1 Scenes & Lines

**Input scenes** live in `input/scenes/sceneXX.jsonl`, one file per scene, one JSON object per line. Because the file name (and the corresponding entry in `metadata/scenes.jsonl`) already identifies the scene, line records only need **line-specific** metadata:

- `id` (string) – stable line identifier (e.g., `scene01_0001`).
- `text` (string) – source text.
- `meta` (object, optional) – per-line metadata.
  - rentl reserves a few conventional keys (e.g., `speaker`, `voice_clip`, `stage_direction`) but the object stays open for arbitrary user-defined fields such as `text_color`, `camera_angle`, or engine-specific cues.
  - Every subagent receives the full `meta` dict untouched, so custom fields can influence behavior without extra plumbing. Scene-level fields (route, raw file, synopsis, etc.) belong in `scenes.jsonl`, not here.

Minimal line example:

```json
{ "id": "scene01_0001", "text": "……", "meta": {} }
```

Line with optional metadata:

```json
{
  "id": "scene01_0002",
  "text": "おはよう。",
  "meta": {
    "speaker": "Aya",
    "voice_clip": "v00023",
    "stage_direction": "smiles softly",
    "text_color": "#FF99CC"
  }
}
```

Important notes:

- **Speaker is optional**. When present:

  - `meta.speaker = null` → no speaker information available.
  - `meta.speaker = "narration"` → explicit narration.
  - `meta.speaker = "???"` → unknown/masked speaker.

- Custom fields remain untouched by rentl but travel with each line through the pipeline so downstream tooling/subagents can react if desired.
- Pipelines/subagents fetch the matching scene entry from `metadata/scenes.jsonl` (via the scene file name) to access scene-level metadata such as `raw_file`, route membership, summaries, or BGM.

### 4.2 Translated Lines

Translations are stored as **aligned JSONL** files. Each record includes both source and target text:

```json
{
  "id": "scene01_0002",
  "text_src": "おはよう。",
  "text_tgt": "Morning.",
  "meta": {
    "speaker": "Aya",
    "idioms": [],
    "references": [],
    "style_notes": [],
    "text_color": "#FF99CC",
    "checks": {
      "pronoun_consistency": "ok",
      "tense_consistency": "ok"
    }
  }
}
```

Here `text_color` is a user-supplied hint (e.g., denoting split personalities). Rentl stores and forwards it unchanged so custom review tools or subagents can consume it. Scene-level metadata required by translators (route, summary, bgm, etc.) is looked up from `metadata/scenes.jsonl` rather than repeated per line.

- `meta` may accumulate annotations as subagents run (idioms, references, checks).
- For multiple passes/revisions, the recommended approach is **directory-per-revision**, e.g.:

  - `output/translations/v1/scene01.jsonl`
  - `output/translations/v2/scene01.jsonl`

Git remains the primary versioning mechanism. rentl doesn’t manage revisions internally beyond directory naming conventions.

### 4.3 Metadata Hierarchy

All long-lived metadata lives under `metadata/`, split by scope so humans and agents know where to read/write:

- `game.json`
  - Title, languages, genres, synopsis, canonical timeline entries, global UI constraints (charset, max line length, word-wrap info), and references to other assets.
- `characters.jsonl`
  - One record per character with bios, pronouns, voice notes, tags, and any other descriptors.
- `glossary.jsonl`
  - Canonical terminology/idioms/glosses with translation rules.
- `locations.jsonl`
  - Optional list of recurring places with descriptions, mood cues, or reference imagery.
- `items.jsonl`
  - Optional for RPGs/ADV with inventory, spells, or other named objects.
- `routes.jsonl`
  - Route metadata: id, name, synopsis, primary characters, endings, ordered list of scene IDs, optional flags.
- `scenes.jsonl`
  - Scene metadata: id, title, owning route(s), raw script file, human-authored notes, plus agent-generated annotations (summaries, character lists, importance ratings, BGM cues).
- `bgm.jsonl`
  - Optional mapping of music ids to descriptions; scenes/lines reference them by id.
> **Temporarily tentative**: The example JSON snippets below illustrate the intended schema but may change once loaders/templates are implemented. When the code lands, update these examples to match reality.

- `style_guide.md`
  - Markdown describing voice, POV, typography, localization rules.
- `context_docs/`
  - Folder of arbitrary Markdown/PDF sources (manuals, wikis) referenced by subagents.

Example `characters.jsonl` (newline-delimited JSON objects):

```json
{"id": "aya", "name_jp": "綾", "name_en": "Aya", "pronouns_en": "she/her", "notes": "Classmate of the protagonist. Casual but kind tone."}
{"id": "mc", "name_jp": "", "name_en": "Takumi", "pronouns_en": "he/him", "notes": "Protagonist, internal monologue often dry and self-deprecating."}
```

Example `glossary.jsonl`:

```json
{"term_jp": "先輩", "term_en": "senpai", "notes": "Keep as 'senpai' with explanation on first occurrence."}
{"term_jp": "文化祭", "term_en": "school festival", "notes": "Use 'school festival' in dialogue, more formal in narration if needed."}
```

Example `scenes.jsonl` entry:

```json
{
  "id": "scene01",
  "title": "Prologue: Rooftop",
  "route_ids": ["common"],
  "raw_file": "scene01.ks",
  "manual": {
    "notes": "Establishes Aya and MC dynamic",
    "tags": ["intro", "school"]
  },
  "auto": {
    "summary": "MC meets Aya on the rooftop and discusses the upcoming festival.",
    "primary_characters": ["mc", "aya"],
    "bgm": [
      {"id": "bgm_theme_01", "start_line": "scene01_0001", "end_line": "scene01_0012"},
      {"id": "bgm_theme_02", "start_line": "scene01_0013"}
    ]
  }
}
```

Notes:

- Each JSON/JSONL entry defines required ids plus extensible notes fields; we keep schemas flexible but well documented.
- These files are **human-authored external context**. DeepAgents subagents treat them as read-only references and may emit additional annotations (idioms, QA findings, summaries) into their own working memory or as structured proposals (e.g., `scenes.jsonl` updates) without overwriting human content.
- When a subagent discovers new entries or edits (characters, glossary, scenes, routes), it raises a **metadata-update request** via the HITL tool described in §5.4 so supervisors can approve/modify the change before persistence.

---

## 5. Pipelines & Subagents

### 5.1 Pipeline Philosophy

- **Code-first pipelines**: defined as Python functions in `rentl_pipelines.flows`.
- Scenes are the **primary unit of work**:

  - Work is done at the **scene level**, not line-by-line in isolation.
  - Pipelines may process scenes in arbitrary order and may perform multiple passes.

- **Task-level parallelism, not content-level parallelism**:

  - For a given scene, different subagents (idiom detection, reference detection, etc.) may run in parallel where appropriate.
  - We avoid naive line-level parallel translation as the primary mechanism; context is prioritized.
  - Internally, a pipeline may still implement an initial parallel line translation pass, followed by a scene-level corrective pass that uses full context.

### 5.2 deepagents / LangChain Integration

- deepagents (via `create_deep_agent`) is the **subagent orchestration layer** on top of LangChain.
- LLMs are represented via LangChain chat models (e.g., `ChatOpenAI`, `init_chat_model`).

  - This allows:

    - `base_url` to point at OpenAI, LM Studio, Ollama, etc.
    - Unified model configuration regardless of provider while still exposing per-subagent overrides.

- DeepAgents middleware stack:

  - `TodoListMiddleware` provides the planning/prioritization "working board" for a scene-level deep agent.
  - `FilesystemMiddleware` gives shared scratch space so subagents can persist notes, drafts, or diagnostics outside the human-authored metadata/glossaries.
  - `SubAgentMiddleware` coordinates the specialized subagents (summaries, translators, formatters, etc.), each with its own goal description, allowed tools, and optional model overrides.
  - `rentl_agents.graph.engine` configures these defaults and exposes helpers to spawn scene/game coordinator agents with the proper middleware stack plus any additional domain-specific middleware we add later.
  - Tool-level interrupts (`interrupt_on`) gate sensitive actions (filesystem writes outside the scratch space, glossary updates, destructive operations) and pause the DeepAgent until a human decision is provided.

- Subagent definitions live in `rentl_agents.subagents.*`:

  - Each subagent advertises a specific goal (e.g., "summarize the scene"), its toolset (LangChain tools, Tavily search wrappers, formatter utilities), and what external context must be loaded (character sheets, glossary entries, etc.).
  - Subagents may also emit new contextual artifacts (e.g., idiom annotations) that feed back into the virtual filesystem for downstream specialists.
  - Pipelines primarily ask the DeepAgent to complete a scene translation task; the DeepAgent's planner decides which subagents to invoke and can spin up temporary nested subagents for deep dives while keeping context isolation.
  - A `glossary_curator` subagent proposes updates by calling the human-gated `glossary_update_request` tool when it detects missing or outdated entries.

- External context vs. working memory:

  - **Human-authored context** (glossaries, character bios, style guides, scene metadata) is treated as source-of-truth reference material passed into the DeepAgent as read-only attachments.
  - **Subagent working memory** (scratchpads, todo lists, intermediate translations) lives inside DeepAgents middleware, ensuring the agent can restructure or expand it without mutating the human-maintained files.

- Tavily and LangSmith:

  - **Tavily**: First web-search provider. If no Tavily key (or other search config) is available, subagents requiring web search will gracefully no-op or be disabled.
  - **LangSmith**: Optional; used for debugging, evaluation, and deeper analysis. Pipelines behave normally without it.

### 5.3 Example MVP Pipeline: `scene_mvp`

The **v1 scene-level pipeline** (`rentl_pipelines.flows.scene_mvp`) is designed to validate the concept quickly:

1. **Load Project & Scene**

   - Read `rentl.project.toml`, the relevant metadata files (`game.json`, `routes.jsonl`, `scenes.jsonl`, etc.), and the target scene JSONL.

2. **Build Context Bundle**

   - Collect character data, glossary entries, route metadata, the scene entry from `scenes.jsonl`, style guide excerpts, and optional context docs into a structured context object.

3. **Subagent Plan for Each Scene**
   High-level flow orchestrated by the DeepAgent planner (exact graph TBD in code):

   - `summarize_scene` subagent

    - Generate a concise description of the scene (in JP or EN) to feed into later subagents.

   - `detect_idioms` subagent

     - Identify idioms and culturally specific expressions per line.

   - `detect_references` subagent (with Tavily if available)

     - Detect references (cultural, media, historical) and attach short explanatory notes to metadata.

   - `translate_scene` subagent

     - Produce one or more candidate translations per line, considering:

       - scene summary
       - metadata (speaker, if any)
       - character and glossary data
       - style guide

   - `synthesize_translation` subagent

     - Refine and select a final translation per line from candidates, ensuring style and tone consistency.

   - `style_checks` subagent

     - Validate that output matches style guide (honorific handling, terminology consistency, etc.).

   - `glossary_curator` subagent (optional but recommended)

     - Review the scene for new entities or terminology gaps and raise human-approved update requests.

   - `formatting_checks` subagent

     - Enforce hard limits (line length, unsupported characters) and either:

       - Adjust formatting (if safe), or
       - Flag for manual review.

4. **Write Output**

   - Write aligned JSONL for that scene to `output/translations/vX/scene_name.jsonl`.

5. **Retry & Error Handling**

   - Automatic retry for transient issues (e.g., timeouts).
   - Configurable “fail-fast vs best-effort” behavior:

     - Default is to **retry transient errors** and **fail fast on real configuration errors** (e.g., invalid model, missing mandatory files).

### 5.4 Human-in-the-Loop Glossary / Metadata Updates

- DeepAgents supports human approval on specific tools via the `interrupt_on` parameter. We define a `glossary_update_request` tool (and eventually a `glossary_updater` subagent) that accepts a payload describing the proposed addition/edit.
- The tool is registered in `create_deep_agent(..., interrupt_on={"glossary_update_request": {"allowed_decisions": ["approve", "edit", "reject"]}})` so execution pauses until a supervisor responds. Decision payloads (including optional edits) are then written to the metadata files by a trusted helper after approval.
- Workflow:
  1. Subagents detect missing entities (new characters, idioms, etc.) during translation QA and assemble a structured recommendation (line references, suggested canonical spelling, justification).
  2. They call `glossary_update_request`, which interrupts the DeepAgent and surfaces the suggestion to a human reviewer via CLI/GUI.
  3. The reviewer can approve as-is, edit the JSON, or reject. Approved entries are merged into the relevant `metadata/*.json[l]` files by a deterministic scripts/tooling layer, keeping the authoritative files human-curated while still benefiting from agent discoveries.
- Because DeepAgents natively handles interrupts, no bespoke orchestration is needed beyond capturing the decision and resuming execution. This keeps the workflow HITL-friendly without blocking the rest of the pipeline.
- Current limitation: DeepAgents pauses the entire root agent while an interrupt is pending, so other subagents cannot make progress until the supervisor responds. We accept this trade-off for now and will file an upstream feature request (or contribute a PR) for non-blocking interrupts so future versions can continue unrelated subagents while approval is pending.

---

## 6. Config & CLI

### 6.1 Project Config (`rentl.project.toml`)

An example (simplified):

```toml
[project]
name = "example_vn"
source_lang = "ja"
target_lang = "en"

[paths]
input_scenes = "input/scenes"
output_translations = "output/translations"
metadata = "metadata"

[llm.default]
provider = "openai"              # or "custom"
model = "gpt-4o-mini"
base_url = "https://api.openai.com/v1"  # or LM Studio/Ollama endpoint
api_key_env = "OPENAI_API_KEY"
temperature = 0.3

[web_search]
provider = "tavily"
api_key_env = "TAVILY_API_KEY"
enabled = true

[observability]
langsmith_enabled = false
project = "rentl-example"

[style]
honorific_handling = "keep"      # "keep" | "strip" | "explain"
```

Pydantic models in `rentl_core.config.project` parse and validate this file.

### 6.2 CLI (Typer) Overview

The CLI (`rentl-cli`) will expose commands such as:

- `rentl init`

  - Uses Copier template to scaffold a new game project in the current directory (one git repo per game is strongly encouraged).

- `rentl run scene-mvp --project-path .`

  - Runs the scene-level MVP pipeline on all scenes found under `input/scenes/`.
  - Additional flags:

    - `--scene scene01.jsonl` to restrict to a specific scene.
    - `--revision v1` to choose an output revision directory.

- `rentl inspect` (future)

  - View or summarize translation results, inconsistencies, etc.

---

## 7. Async & Concurrency

- **Async-first** design:

  - Agents and pipelines are defined as async functions where appropriate.

- **Task-level parallelism**:

  - Within a scene, multiple subagents that annotate lines (idiom detection, reference detection) may be run in parallel where it is safe.
  - We avoid blindly translating lines independently as the main strategy; context-first design is the default.

- **Retry & Failure Modes**:

  - Transient errors (network, rate limits) are retried a small configurable number of times.
  - Non-transient configuration errors cause clear failures.
  - Mode flags (e.g., `fail-fast` vs `best-effort`) may be configured per pipeline run in the project config or via CLI flags.

---

## 8. Testing Strategy

- **Unit tests**:

  - Use mocked LLM backends (e.g., echo or deterministic transforms) for:

    - Data models.
    - I/O.
  - Subagent logic that doesn’t need real language understanding.

- **Integration tests**:

  - Use a small open-source or synthetic VN snippet (e.g., `examples/tiny_vn`) as fixtures.
  - Run the actual pipelines against a **lightweight open-source model** (e.g., a local OpenAI-compatible endpoint).
  - Assert structural properties of outputs and basic sanity checks.

- **Future demo**:

  - Plan to support a full demo project using an open-source VN (e.g. Katawa Shoujo) when licensing/logistics are fully confirmed.

---

## 9. Licensing & Contributions

- **License**: MIT.
- **Contributions**:

  - Pull requests are encouraged for:

    - New export formats (e.g. Translator++ compatible exports).
    - New subagents (e.g. specialized pun detectors, dialect handling).
    - Additional metadata schemas and small UX improvements to the template.

  - For now, extending rentl generally involves forking and modifying pipelines/subagents directly; no plugin system is provided in v1.

---

## 10. Roadmap (High-Level)

**v0.1 – MVP (Scene Pipeline)**

- Monorepo + uv workspace set up.
- Copier template with:

  - `rentl.project.toml`
  - `metadata/*`, `input/scenes/`, `output/`.

- Core models for `Line` and `Scene`.
- JSONL I/O utilities.
- LLM backend abstraction with LangChain `ChatOpenAI` support.
- Tavily integration (optional).
- Scene-level MVP pipeline with:

  - Scene summary.
  - Basic idiom/reference detection.
  - Single or dual backend translation.
  - Simple synthesis and style/format checking.

- CLI commands: `rentl init`, `rentl run scene-mvp`.
- Basic unit + integration tests.

**v0.2 – Game-Level Enhancements**

- Route and game-level summaries.
- Cross-scene consistency checks (pronouns, terminology, tone).
- Better annotation and reporting infrastructure.

**v0.3+ – Ecosystem & Exporters**

- Translator++ compatible export adapter.
- More robust inspection/reporting tools (`rentl inspect`).
- Optional web UI / server for interactive review.
