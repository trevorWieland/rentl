# Repository Guidelines for AI-Coding Agents

This document provides guidance for AI coding agents (like Claude Code, GitHub Copilot, Cursor, etc.) working on the rentl codebase.

---

## Project Purpose and Summary

rentl is a Python 3.13, multi-agent translation pipeline for visual novels (initially JP→EN). It turns cleaned, pre-extracted scene text plus metadata into aligned `(source, translation, metadata)` corpora.

**Core principles**:
- Context-first (scene/game metadata, style guides, glossaries)
- Multi-agent orchestration via DeepAgents/LangChain
- Human-in-the-loop controls for sensitive edits
- Reproducible CLI/pipeline runs per game repo
- Git-based version control for all metadata and translations

---

## Important Distinction

**You are a coding agent**. This repo is for building rentl's Context Building, Translation, and Editing Agents. **Do not confuse yourself as one of these agents**.

- **Your role**: Expand the capabilities of rentl's agents, subagents, and tools by modifying the codebase
- **Not your role**: Act as a translator or context builder yourself

**Example boundary**: When adding test data to `examples/tiny_vn`, leave some metadata purposefully blank. The Context Builder agent needs gaps to fill—if you complete everything, there's nothing to test.

---

## Scope

### In Scope

- Scene-level pipelines that read JSONL scenes and metadata
- Specialized subagents (summaries, idioms/references, translation, synthesis, style/format checks)
- Writing aligned JSONL outputs with provenance tracking
- Copier template + CLI support for per-game repos
- Optional integrations: Tavily search, LangSmith observability
- Async-first orchestration
- Additive metadata annotations via HITL-gated tools

### Out of Scope (Non-Goals)

rentl explicitly **does not** handle:

1. **Text extraction/OCR**: Users must extract and clean text from game engines before using rentl
2. **Live/in-game translation**: No hooking into running games, no real-time overlays
3. **Patch building**: rentl outputs aligned translation files; external tools handle engine-specific patch generation
4. **Heavy "rewrite the story" localization**: Focus is on faithful translation with light localization, not creative rewriting

**Why these are non-goals**: rentl focuses on the translation pipeline itself. Text extraction and patch building are engine-specific and better handled by specialized tools.

---

## Architecture Overview

rentl is structured as a **5-part system**:

### 1. Project Template (Copier)

Users create one git repo per game using a Copier template that scaffolds:

```
game_project/
  metadata/
    game.json
    characters.jsonl
    glossary.jsonl
    locations.jsonl
    routes.jsonl
    scenes.jsonl
    style_guide.md
    context_docs/
  input/
    scenes/*.jsonl
  output/
    translations/
    reports/
  rentl.project.toml  # Project configuration
```

**File**: `libs/templates/src/rentl_templates/copier/`

### 2. CLI Interface (Typer)

The `rentl` CLI orchestrates the full workflow:

```bash
rentl init              # Create new game project
rentl validate          # Check metadata integrity
rentl context           # Run Context Builder phase
rentl translate         # Run Translator phase
rentl edit              # Run Editor phase
```

**File**: `apps/cli/src/rentl_cli/`

### 3. Core Library (Pydantic Models + I/O)

Defines data models, loaders, and configuration:

- **Models**: `Line`, `Scene`, `Character`, `Glossary`, etc. (with `*_origin` provenance fields)
- **Loaders**: Async JSONL/JSON readers using `orjson` + `anyio`
- **Config**: Project settings, LLM backends, observability

**File**: `libs/core/src/rentl_core/`

### 4. Subagent Layer (DeepAgents + LangChain)

Specialized agents for each phase:

- **Context Builder**: `scene_detailer`, `character_detailer`, `location_detailer`, `glossary_detailer`, `route_detailer`
- **Translator**: `scene_translator`
- **Editor**: `scene_style_checker`, `scene_consistency_checker`, `scene_translation_reviewer`

Each subagent has:
- A goal description
- A set of tools (read/add/update operations with HITL gating)
- Access to external context (characters, glossary, style guide)

**File**: `libs/agents/src/rentl_agents/subagents/`

### 5. Pipelines (Orchestration)

Async workflows that coordinate subagents across scenes:

- **scene-level**: Process one scene at a time
- **route-level** (future): Process related scenes together
- **game-level** (future): Multi-pass processing across entire project

**File**: `libs/pipelines/src/rentl_pipelines/flows/`

---

## Repo Tech Stack

**Language & Runtime**:
- Python 3.13
- uv workspace for dependency management

**Core Libraries**:
- **pydantic** (+ pydantic-settings): Data models, validation, configuration
- **orjson**: Fast JSONL I/O
- **anyio**: Async file operations

**Agent Layer**:
- **deepagents**: Multi-agent orchestration with middleware
- **langchain-openai**: LLM integration (OpenAI-compatible endpoints)
- Optional: **Tavily** (web search), **LangSmith** (observability)

**CLI & Tooling**:
- **Typer**: Command-line interface
- **ruff**: Linting and formatting (Google docstring style, 120 char line length)
- **ty**: Type checking
- **pytest**: Testing framework

**Workspace Packages**:
- `rentl-core`: Data models, I/O, config
- `rentl-agents`: Subagents, tools, LLM backends
- `rentl-pipelines`: Orchestration flows
- `rentl-templates`: Copier template
- `rentl-cli`: CLI application
- `rentl-server`: (Placeholder for future web UI)

---

## Performance and Concurrency

### Async-First Design

rentl uses **async/await** throughout:

```python
# ✅ Good: Async function
async def load_scene(scene_id: str) -> list[SourceLine]:
    return await load_scene_file(scene_path)

# ❌ Bad: Blocking synchronous I/O
def load_scene(scene_id: str) -> list[SourceLine]:
    with open(scene_path) as f:
        return json.load(f)
```

**Why**: Allows concurrent I/O operations (loading multiple scenes, calling LLMs in parallel) without blocking.

### Task-Level Parallelism

rentl uses **task-level parallelism** (run independent subagents concurrently), **not content-level parallelism** (translate all lines at once).

```python
# ✅ Good: Run independent subagents in parallel
async with anyio.create_task_group() as tg:
    tg.start_soon(detect_idioms, scene)
    tg.start_soon(detect_references, scene)
    tg.start_soon(summarize_scene, scene)

# ❌ Bad: Translate all lines in parallel (loses context)
async with anyio.create_task_group() as tg:
    for line in scene.lines:
        tg.start_soon(translate_line, line)  # No cross-line context!
```

**Why**: Context-first design requires agents to see the full scene, not isolated lines. Parallelism happens at the subagent level, not the line level.

### Context-First Design

Translators must have access to:
- Full scene context (all lines, not just one)
- Character bios and pronouns
- Glossary entries
- Style guide
- Related scenes (for consistency)

**Guideline**: Avoid optimizations that sacrifice context for speed. Scene-level processing preserves quality.

### Retry and Failure Handling

- **Transient errors** (network, rate limits): Retry with exponential backoff
- **Non-transient errors** (invalid config, missing files): Fail fast with clear error messages

```python
# ✅ Good: Retry transient errors
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
async def call_llm(prompt: str) -> str:
    return await llm.ainvoke(prompt)

# ✅ Good: Fail fast on config errors
if not settings.OPENAI_API_KEY:
    raise ConfigurationError("OPENAI_API_KEY is required")
```

---

## Quality Checks

Before committing code, run:

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Format code**:
   ```bash
   uv run ruff format
   ```

3. **Lint**:
   ```bash
   uv run ruff check --fix
   ```
   Honor repo config; don't relax rules without approval.

4. **Type check**:
   ```bash
   uv run ty check
   ```

5. **Run tests**:
   ```bash
   uv run pytest
   ```
   Prefer deterministic/mocked LLM backends; use example fixtures.

**Standards**:
- Line length ≤120 characters
- Google-style docstrings
- Type hints on all public functions
- Async code must be type-safe

---

## What Code Agents Should Do

### General Guidelines

1. **Additive, context-aware changes**:
   - Maintain async patterns
   - Honor metadata schemas (see `SCHEMAS.md`)
   - Keep `examples/tiny_vn` up to date with new features (but leave gaps for testing!)

2. **Documentation**:
   - Update `README.md` when behavior/commands change
   - Keep tables of agents/tools current
   - Update `SCHEMAS.md` when adding new fields

3. **Testing**:
   - Add small, focused tests alongside new logic
   - Mock LLM backends for deterministic tests
   - Reuse `orjson`/`pydantic` models for I/O

4. **Code quality**:
   - Run `ruff` and `ty` before committing
   - Use concise comments for non-obvious flows (agent orchestration, middleware wiring)
   - Keep line length ≤120, Google docstrings

5. **Communication**:
   - Use **numbered lists** when providing details to human programmers (enables easy feedback referencing)

### Examples

**✅ Good: Adding a new tool with HITL approval**

```python
@tool(approval_policy="standard")
async def update_character_bio(
    context: ProjectContext,
    character_id: str,
    new_bio: str
) -> str:
    """Updates character bio with provenance tracking and HITL approval.

    Args:
        context: Project context with character metadata.
        character_id: Character identifier.
        new_bio: New biographical notes.

    Returns:
        Success message.
    """
    char = context.get_character(character_id)

    # Check provenance for HITL approval
    if char.notes_origin == "human":
        # Tool will pause for approval via interrupt_on
        pass

    char.notes = new_bio
    char.notes_origin = f"agent:character_detailer:{date.today()}"
    await context.save_characters()
    return f"Updated bio for {character_id}"
```

**❌ Bad: Translating lines without context**

```python
# Don't do this - loses scene context!
async def translate_lines(lines: list[SourceLine]) -> list[str]:
    return await asyncio.gather(*[
        translate_single_line(line.text)
        for line in lines
    ])
```

---

## What Code Agents Need Human Feedback For

Request human approval before:

1. **Adding new dependencies** or changing `uv` workspace membership
2. **Introducing new top-level agents/pipelines** or changing metadata schemas
3. **Enabling new external services** (Tavily, LangSmith, etc.) that require API keys
4. **Overwriting human-authored metadata**: Propose HITL updates instead
5. **Large behavioral shifts** to CLI commands or project layout
6. **Changing HITL approval policies** for tools (e.g., making `update_*` permissive)

### HITL Tool Design

When implementing tools for subagents:

- **read_* tools**: Always `permissive` (never need approval)
- **add_* tools**: Use `permissive` for low-risk additions (glossary entries), `strict` for structural changes (new routes)
- **update_* tools**: Use `standard` (check `*_origin` provenance) by default
- **delete_* tools**: Use `standard` (check if any field is human-authored) or `strict`

See `libs/agents/README.md` for detailed HITL implementation guidelines.

---

## What Code Agents Should Never Do

**❌ Do not**:

1. **Rewrite repo structure**, lint/typecheck settings, or formatting rules
2. **Act as the rentl agents/subagents** - your job is modifying the repo, not translating games
3. **Add keys/secrets** or bake credentials into code/tests
4. **Destructive edits to example/template data** unless explicitly requested
5. **Speculative refactors** that change pipeline semantics, concurrency patterns, or CLI flags without approval
6. **Relax type checking or linting rules** - fix the code instead
7. **Add `# type: ignore` comments** without good reason - improve types instead

---

## File Naming Conventions

### Metadata Files

- `metadata/game.json`: Single JSON object
- `metadata/*.jsonl`: Newline-delimited JSON (one object per line)
- `metadata/style_guide.md`: Markdown
- `metadata/context_docs/*.md`, `*.txt`, `*.pdf`: Reference materials

### Scene Files

- `input/scenes/<scene_id>.jsonl`: One file per scene, filename stem matches scene ID
- `output/translations/<scene_id>.jsonl`: Aligned translations, filename stem matches input

### Python Modules

- `libs/core/src/rentl_core/model/<entity>.py`: Pydantic models (e.g., `character.py`, `scene.py`)
- `libs/agents/src/rentl_agents/subagents/<subagent_name>.py`: Subagent implementations
- `libs/agents/src/rentl_agents/tools/<tool_category>.py`: Tool collections (e.g., `scene.py`, `metadata.py`)

---

## Testing Strategy

### Unit Tests

Mock LLM backends for deterministic tests:

```python
from unittest.mock import AsyncMock

async def test_scene_detailer():
    mock_llm = AsyncMock(return_value="Scene summary here")
    result = await summarize_scene(mock_llm, scene)
    assert "summary" in result
```

### Integration Tests

Use `examples/tiny_vn` as fixtures:

```python
async def test_full_context_pipeline():
    context = await load_project_context(Path("examples/tiny_vn"))
    result = await run_context_pipeline(context)
    assert len(result.summaries) == 4  # 4 scenes in tiny_vn
```

### Guidelines

- **Mock external services** (LLMs, Tavily, LangSmith) in tests
- **Use deterministic fixtures** for reproducible results
- **Test edge cases**: empty fields, missing metadata, invalid provenance
- **Don't commit test API keys** - use mock credentials

---

## Communication Best Practices

When working with human developers:

1. **Use numbered lists** for multi-step explanations (enables "see item 3" feedback)
2. **Include file paths** with line numbers for code references (e.g., `rentl_core/model/scene.py:47`)
3. **Show before/after** for changes to existing code
4. **Provide concrete examples** over abstract descriptions
5. **Ask clarifying questions** before making assumptions about requirements

**Example**:

> I've identified 3 issues with the character_detailer implementation:
>
> 1. Missing provenance tracking on `pronouns` field (rentl_agents/subagents/character_detailer.py:23)
> 2. Not checking HITL approval before updating human-authored notes (line 45)
> 3. No error handling for missing character IDs (line 12)
>
> Proposed fixes:
> 1. Add `pronouns_origin` field update
> 2. Use `@tool(approval_policy="standard")` decorator
> 3. Raise `ValueError` with clear message
>
> Should I proceed with these changes?

---

## Resources

- **[SCHEMAS.md](SCHEMAS.md)**: Complete data format documentation with provenance tracking
- **[README.md](README.md)**: User-facing overview and roadmap
- **[libs/agents/README.md](libs/agents/README.md)**: HITL tool implementation guide
- **[examples/tiny_vn](examples/tiny_vn)**: Example project structure

---

## Summary

**Remember**:
- You are building tools **for** translation agents, not acting as one
- Maintain async-first, context-first design patterns
- Follow provenance tracking and HITL approval policies
- Test with mocked backends, keep code clean and typed
- Ask humans before major architectural changes
