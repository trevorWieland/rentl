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

## Agent Architecture: LangChain vs DeepAgents

rentl uses **two different agent frameworks** for different purposes. Understanding this distinction is critical for correct implementation.

### Top-Level Agents (DeepAgents)

**Use `create_deep_agent` from the `deepagents` package.**

Top-level agents are intelligent orchestrators that coordinate subagents:
- **Context Builder Agent** - Decides which detailer subagents to run and when
- **Translator Agent** - Manages scene translation workflows
- **Editor Agent** - Coordinates QA and review subagents

**Key characteristics:**
- Use `create_deep_agent(model, tools, subagents=[], system_prompt, interrupt_on={}, checkpointer)`
- Have access to stats/progress tools for high-level decision making
- Spawn subagents via the `task()` tool provided by `SubAgentMiddleware`
- Support HITL interrupts via `interrupt_on` parameter (requires checkpointer)
- Automatically include TodoListMiddleware, FilesystemMiddleware, SubAgentMiddleware

**Example:**
```python
from deepagents import create_deep_agent, CompiledSubAgent
from langgraph.checkpoint.memory import MemorySaver

context_builder = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_context_status, analyze_progress],  # Stats tools, NOT read tools
    system_prompt="You coordinate context enrichment...",
    subagents=[scene_detailer, character_detailer, ...],
    interrupt_on={"update_scene_summary": True},  # HITL for provenance violations
    checkpointer=MemorySaver()
)
```

### Subagents (LangChain Agents)

**Use `create_agent` from the `langchain.agents` package.**

Subagents are specialized workers that perform focused tasks:
- **scene_detailer** - Enriches scene metadata
- **character_detailer** - Enriches character metadata
- **translate_scene** - Translates a single scene
- etc.

**Key characteristics:**
- Use `create_agent(model, tools, system_prompt, middleware=[])`
- Have specialized tools for their specific domain (no general filesystem access)
- Work in isolation - context stays clean for top-level agent
- Return results via `CompiledSubAgent` wrapper
- Can have their own middleware (TodoListMiddleware for complex tasks, NO FilesystemMiddleware)

**Example:**
```python
from langchain.agents import create_agent
from deepagents import CompiledSubAgent

# Create LangChain agent graph
scene_detailer_graph = create_agent(
    model=model,
    tools=build_scene_tools(context, scene_id),
    system_prompt="You enrich scene metadata..."
    # No middleware = no default tools, only our specialized tools
)

# Wrap for use as subagent
scene_detailer = CompiledSubAgent(
    name="scene-detailer",
    description="Enriches scene metadata with summary, tags, characters, locations",
    runnable=scene_detailer_graph
)
```

### Middleware Differences

**DeepAgents middleware** (auto-included by `create_deep_agent`):
- `TodoListMiddleware` - Provides `write_todos` tool for task planning
- `FilesystemMiddleware` - Provides ls, read_file, write_file, edit_file, glob, grep
- `SubAgentMiddleware` - Provides `task()` tool for spawning subagents

**LangChain middleware** (must be explicitly added to `create_agent`):
- Different set of middleware for agent customization
- `TodoListMiddleware` - Same concept, different implementation
- NO automatic FilesystemMiddleware
- NO SubAgentMiddleware (subagents don't spawn other subagents)

**Critical rule:** When using `middleware=[]` in DeepAgents, you remove ALL middleware including SubAgentMiddleware, preventing the agent from spawning subagents!

### Human-in-the-Loop (HITL) Differences

**DeepAgents HITL** (for top-level agents):
```python
# Configure via interrupt_on parameter
agent = create_deep_agent(
    tools=[update_scene_summary, read_scene],
    interrupt_on={
        "update_scene_summary": {"allowed_decisions": ["approve", "edit", "reject"]},
        "read_scene": False,  # No interrupts
    },
    checkpointer=MemorySaver()  # Required for HITL
)

# Handle interrupts
if result.get("__interrupt__"):
    interrupts = result["__interrupt__"][0].value
    # Present to user, get decisions
    result = agent.invoke(Command(resume={"decisions": decisions}), config=config)
```

**LangChain HITL** (for subagents, if needed):
```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

subagent = create_agent(
    tools=[update_metadata],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={"update_metadata": True}
        )
    ],
    checkpointer=MemorySaver()
)
```

### Provenance-Based HITL Integration

rentl uses **two-layer HITL**:

**Layer 1 - Provenance checking in tools:**
```python
from langchain.tools import tool, ToolRuntime

@tool
async def update_scene_summary(scene_id: str, summary: str, runtime: ToolRuntime) -> str:
    """Update scene summary with HITL approval for human-authored data."""
    context = runtime.context.project_context
    scene = context.get_scene(scene_id)

    # Check provenance
    if scene.annotations.summary_origin == "human":
        return "Requesting approval to overwrite human-authored summary"

    # Update if agent-authored or empty
    await context.update_scene_summary(scene_id, summary)
    return f"Updated summary for {scene_id}"
```

**Layer 2 - DeepAgents interrupt configuration:**
```python
interrupt_on={
    "update_scene_summary": True,  # Pauses when tool requests approval
    "read_scene": False,           # No interrupts for read-only tools
}
```

**How it works:**
1. Tool checks provenance (`if origin == "human"`)
2. Tool returns message requesting approval
3. DeepAgents sees tool in `interrupt_on` and pauses
4. Human approves/edits/rejects
5. If approved, tool updates with agent origin

### Context Management

**Top-level agents:**
- See high-level stats and summaries
- Use stats tools: `get_context_status()`, `get_translation_progress()`
- Do NOT use read tools that return full scene transcripts (causes context bloat)
- Receive concise results from subagents

**Subagents:**
- Work in isolated context
- Have full access to detailed data via specialized tools
- Return only essential results to top-level agent
- Can read full scenes, character details, etc. without bloating main context

### Shared ProjectContext Architecture

rentl enforces **single-game-per-repo** with a **shared mutable ProjectContext** instance.

**Design principles:**
1. **One shared instance**: `ProjectContext` loaded once at top-level agent creation
2. **Passed by reference**: All subagents receive the same context instance
3. **Immediate visibility**: In-memory updates are instantly visible to all concurrent agents
4. **Tool-only access**: Subagents interact ONLY via tools (`read_*`, `update_*`, `add_*`, `delete_*`)
5. **Provenance enforcement**: All writes go through tools that track `*_origin` fields
6. **Write-through persistence**: Updates immediately written to disk (crash-safe)

**Implementation pattern:**
```python
# Top-level agent factory
async def create_context_builder_agent(project_path: Path) -> Agent:
    # Load shared context ONCE
    context = await load_project_context(project_path)

    # Create subagents, passing SAME context instance
    subagents = [
        create_scene_detailer_subagent(context),
        create_character_detailer_subagent(context),
    ]

    # Middleware injects context into runtime
    class ContextMiddleware:
        async def before_agent(self, state, runtime):
            runtime.context.project_context = context
            return {}

    agent = create_deep_agent(
        model=...,
        tools=build_stats_tools(),
        subagents=subagents,
        middleware=[ContextMiddleware()],
    )

    return agent

# Subagent factory (captures shared context via closure)
def create_scene_detailer_subagent(context: ProjectContext) -> CompiledSubAgent:
    tools = build_scene_tools()

    # Middleware injects SAME context instance
    class SubagentContextMiddleware:
        async def before_agent(self, state, runtime):
            runtime.context.project_context = context  # Same instance!
            return {}

    graph = create_agent(
        model=...,
        tools=tools,
        middleware=[SubagentContextMiddleware()]
    )

    return CompiledSubAgent(name="scene-detailer", runnable=graph)

# Tools access shared context (stateless, pure)
@tool
async def update_scene_summary(scene_id: str, summary: str, runtime: ToolRuntime) -> str:
    # All agents see the SAME context instance
    context = runtime.context.project_context

    # Update with locking + persistence
    await context.update_scene_summary(scene_id, summary, origin="agent:scene_detailer")

    return f"Updated scene {scene_id}"
```

**Why single-game-per-repo:**
- Eliminates confusion about which game is being processed
- Simplifies tool design (no need to pass game_id everywhere)
- Prevents agents from accidentally mixing contexts from different games
- If translating a sequel, include prequel context in `metadata/context_docs/`

### Concurrency: Feedback-Providing Locks

**Problem:** When multiple subagents run concurrently, they might try to update the same field.

**Solution:** Entity-level locks with intelligent conflict detection.

**Pattern:**
```python
class ProjectContext:
    def __init__(self, project_path: Path):
        # Entity-level locks (per scene, per character, etc.)
        self._scene_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._character_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Track recent updates for conflict detection
        self._recent_updates: dict[tuple[str, str, str], float] = {}

    async def update_character_bio(
        self,
        char_id: str,
        new_bio: str,
        origin: str,
        conflict_threshold_seconds: float = 30
    ) -> str:
        async with self._character_locks[char_id]:
            char = self.characters[char_id]
            current_bio = char.bio

            # Check if field was recently updated by another agent
            update_key = ("character", char_id, "bio")
            last_update = self._recent_updates.get(update_key, 0)
            time_since_update = time.time() - last_update

            # Provide feedback if concurrent update detected
            if time_since_update < conflict_threshold_seconds and current_bio:
                return f"""CONCURRENT UPDATE DETECTED
Bio was updated {time_since_update:.1f}s ago.
Current: {current_bio}
Your proposed: {new_bio}

Review and retry if your update is still needed."""

            # No conflict - proceed
            char.bio = new_bio
            char.bio_origin = origin
            self._recent_updates[update_key] = time.time()

            # Write immediately (crash-safe)
            await write_character_metadata(self.project_path, char)

            return f"Successfully updated bio for {char_id}"
```

**How it works:**
1. **Subagent 1** updates character bio → succeeds, releases lock
2. **Subagent 2** (concurrent) waits for lock, then acquires it
3. **Subagent 2** detects recent update (2 seconds ago)
4. **Tool returns feedback** with both current and proposed values
5. **Subagent 2 decides**: Skip (redundant), combine both, or overwrite

**Benefits:**
- ✅ No data loss (second update doesn't blindly overwrite)
- ✅ Intelligent coordination (agents see each other's work)
- ✅ No deadlocks (locks held only during update)
- ✅ Crash-safe (immediate writes to disk)

### When to Use Which

| Use Case | Framework | Function |
|----------|-----------|----------|
| Context Builder coordinator | DeepAgents | `create_deep_agent` |
| Translator coordinator | DeepAgents | `create_deep_agent` |
| Editor coordinator | DeepAgents | `create_deep_agent` |
| Scene detailer | LangChain | `create_agent` → `CompiledSubAgent` |
| Character detailer | LangChain | `create_agent` → `CompiledSubAgent` |
| Translation worker | LangChain | `create_agent` → `CompiledSubAgent` |
| Style checker | LangChain | `create_agent` → `CompiledSubAgent` |

### Common Mistakes to Avoid

❌ **Don't** use `create_deep_agent` for subagents
❌ **Don't** use `create_agent` for top-level coordinators
❌ **Don't** give top-level agents read tools that return full content (context bloat)
❌ **Don't** use `middleware=[]` in DeepAgents (removes SubAgentMiddleware)
❌ **Don't** confuse LangChain middleware with DeepAgents middleware
❌ **Don't** skip checkpointer when using HITL in either system
❌ **Don't** hardcode language/style rules in prompts—inject small configs (source/target lang, game title, etc.) or have agents call tools (style guide, UI settings, metadata) to stay context-driven.

✅ **Do** use stats/progress tools for top-level agents
✅ **Do** use specialized tools for subagents
✅ **Do** wrap `create_agent` results in `CompiledSubAgent`
✅ **Do** check provenance in tools before updating
✅ **Do** configure `interrupt_on` for update tools
✅ **Do** provide checkpointer for HITL support

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

2. **Repo-standard commands**:
   - `make fix` (format + lint autofix)
   - `make check` (format check, lint, type, tests)
   These apply formatting/lint fixes and run formatting, linting, typing, and testing. If you hit a permission error (e.g., uv cache), ask for permission rather than changing env vars.

   If you must run individually:
   ```bash
   uv run ruff format
   uv run ruff check --fix
   uv run ty check
   uv run pytest
   ```
   Prefer deterministic/mocked LLM backends; use example fixtures. Use the context7 MCP server to clarify library APIs early (pydantic, langchain, etc.). If ty can’t express a pattern, a targeted `# type: ignore[...]` with a reason is acceptable.

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
