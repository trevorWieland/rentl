# rentl

A multi-agent, context-aware translation pipeline for visual novels—turning raw scene text and metadata into high-quality, consistent JP→EN localizations.

## Overview

rentl mirrors how human teams localize VNs today with distinct phases:

1. **Context Builder (v1.0)** – operates entirely in the source language to enrich metadata: scene summaries, character/location bios, glossary entries, and context docs.
2. **Translator (v1.0)** – consumes the curated context via read-only tools and writes JP→EN translations.
3. **Editor (v1.0)** – reviews source/target pairs, enforces style guides, and flags issues for retranslation.

Each phase uses DeepAgents subagents built on LangChain, making iterative workflows (context → translation → editing) predictable and reproducible.

## Installation

Requirements:

- Python 3.13
- uv for dependency/runtime management
- Access to an OpenAI-compatible chat endpoint (OpenAI, LM Studio, Ollama, etc.)

Setup:

```bash
uv sync
cp template.env .env  # fill in URLs and API keys
```

### Suggested Models

| Purpose              | Model                                      | Status            |
|----------------------|--------------------------------------------|-------------------|
| Agentic reasoning    | `gpt-oss:20b` (LM Studio)                  | Used today        |
| JP→EN translation    | `sugoitoolkit/Sugoi-14B-Ultra-GGUF`        | Planned for v1.0  |

## Basic Usage

```bash
# Validate metadata + scene files
uv run python -m rentl_cli.main validate

# Context builder agent (scene detailer) across all scenes
uv run python -m rentl_cli.main summarize-mvp

# Summarize a single scene
uv run python -m rentl_cli.main summarize-scene scene_c_00
```

Commands accept `--project-path`, `--overwrite`, and `--verbose` flags. Translation and editor commands will join the CLI as they come online.

## Agents (v1.0)

| Agent            | Responsibilities                                                                  | Implementation Status |
|------------------|------------------------------------------------------------------------------------|-----------------------|
| Context Builder  | Scene, character, location, glossary, and route metadata enrichment                | **In progress** (scene detailer in repo) |
| Pretranslator (v1.1) | (Future) idiom detection, accent/region notes, grammar hints between context/translation | Deferred (v1.1)        |
| Translator       | Consume context, run scene translations, write aligned Translation outputs               | Planned               |
| Editor           | QA checks (style, consistency, translation quality), flag issues for retranslation | Planned               |


## Subagents

### Context Builder Subagents (v1.0)

| Subagent            | Purpose                                                                                  | Status           |
|---------------------|------------------------------------------------------------------------------------------|------------------|
| `scene_detailer`    | Replaces simple summarizer; records summary + key scene metadata                         | Implemented      |
| `character_detailer`| Expands character bios, pronoun guidance, notes                                          | Planned          |
| `location_detailer` | Captures location descriptions, mood cues                                                | Planned          |
| `glossary_detailer` | Adds/updates glossary entries via HITL                                                   | Planned          |
| `route_detailer`    | Updates route metadata (descriptions, scene ordering) with human supervision              | Planned          |
| `scene_detailer`    | Hidden summary content to avoid biasing replacements                             | In progress (scene_summarize MVP implemented)      |

### Translator Subagents (v1.0)

| Subagent         | Purpose                                    | Status  |
|------------------|--------------------------------------------|---------|
| `scene_translator`| Reads context and writes translation line pairs | Planned |

### Editor Subagents (v1.0)

| Subagent              | Purpose                                                                      | Status  |
|-----------------------|------------------------------------------------------------------------------|---------|
| `scene_style_checker` | Enforces style guide (tone, honorific policies, markdown formatting)        | Planned |
| `scene_consistency_checker` | Cross-scene review for terminology/pronouns/names consistency        | Planned |
| `scene_translation_review` | Reviews translation quality, flags lines for retranslation             | Planned |

### Future Subagents (v1.1+)

| Subagent              | Agent           | Purpose                                        |
|-----------------------|-----------------|------------------------------------------------|
| `idiom_analyzer`      | Pretranslator    | Detect idioms/cultural references for translators |
| `accent_profiler`     | Pretranslator    | Note accent/region, speech quirks             |
| `grammar_notebook`    | Pretranslator    | Capture grammar notes, tricky sentence structures |

## Tools

| Tool                   | Description                                                              | Agents/Subagents        | Status        |
|------------------------|--------------------------------------------------------------------------|-------------------------|---------------|
| `read_scene_overview`  | Scene metadata + transcript + stored summary (hidden when overwriting)   | Context, Translator     | Implemented   |
| `list_context_docs`    | Lists documents under `metadata/context_docs/`                           | All agents              | Implemented   |
| `read_context_doc`     | Returns contents of a context document                                   | All agents              | Implemented   |
| `write_scene_summary`  | Writes one summary per scene (single-use; overwrite requires flag)       | Context                 | Implemented   |
| `character_detail`     | Returns character bios/pronoun guidance                                  | Context/Translator      | Planned       |
| `glossary_lookup`      | Searches glossary entries                                                | Translator/Editor       | Planned       |
| `context_search`       | Vector/keyword search over context docs                                  | Translator              | Planned       |
| `write_translation`    | Records line-level translations                                          | Translator              | Planned       |
| `record_check`         | Records QA check results (style, consistency, translation review)        | Editor                  | Planned       |

As we implement each subagent/tool, we’ll update the tables above so contributors know what’s available in v1.0 and what’s deferred to v1.1.
