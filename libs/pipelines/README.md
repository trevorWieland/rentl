# rentl-pipelines: Top-Level Agent Orchestration

Contains top-level DeepAgents that intelligently coordinate subagents for context building, translation, and editing workflows.

---

## Purpose

`rentl-pipelines` provides **intelligent top-level agents** that:

- Dynamically decide which subagents to run and when
- Manage scene-level, route-level, and game-level processing
- Handle errors and adaptive workflows
- Collect and report results

**These are NOT simple async functions** - they are intelligent DeepAgents that can:
- Analyze current state to determine what work is needed
- Spawn appropriate subagents via the `task()` tool
- Iterate based on quality of subagent results
- Make dynamic decisions about workflow execution

**Not responsible for**:
- Individual subagent logic (belongs in `rentl-agents`)
- Data models or I/O (belongs in `rentl-core`)
- CLI interface (belongs in `rentl-cli`)

---

## Architecture

### Top-Level Agents (This Package)

Each pipeline contains a **top-level DeepAgent** that acts as an intelligent coordinator:

**Context Builder Agent:**
- Uses `create_deep_agent` from `deepagents`
- Has stats/progress tools to understand current state
- Spawns scene_detailer, character_detailer, location_detailer, glossary_curator, route_detailer subagents
- Can decide to skip, retry, or iterate on subagent results

**Translator Agent:**
- Uses `create_deep_agent` from `deepagents`
- Has translation progress tools
- Spawns translate_scene subagent for each scene
- Can decide whether to use direct translation or MTL backend

**Editor Agent:**
- Uses `create_deep_agent` from `deepagents`
- Has QA status tools
- Spawns style_checker, consistency_checker, translation_reviewer subagents
- Can flag issues and request retranslation

### Subagents (rentl-agents Package)

Subagents are specialized workers created with `create_agent` from `langchain.agents`:
- Work in isolated context (don't bloat main agent's context)
- Have specialized tools for their domain
- Return concise results to top-level agent
- See `libs/agents/README.md` for implementation details

---

## Scope

### In Scope

- Scene-level pipelines (v1.0): Process one scene at a time
- Route-level pipelines (future): Process related scenes together
- Game-level pipelines (future): Multi-pass processing across entire project
- Error handling and retry logic
- Progress reporting and result aggregation
- Task-level parallelism (run independent subagents concurrently)

### Out of Scope

- Content-level parallelism (translating all lines at once—loses context)
- Subagent implementation (belongs in `rentl-agents`)
- Direct LLM calls (subagents handle this)

---

## Key Modules

### flows/

Pipeline implementations:

```
flows/
  scene_mvp.py       # v1.0 scene-level pipeline (context → translate → edit)
  full_game.py       # (Future) Game-level multi-pass pipeline
```

### runner.py

High-level APIs for running pipelines:

```python
from rentl_pipelines.runner import run_context_pipeline

results = await run_context_pipeline(
    context,
    scenes=["scene_c_00", "scene_a_00"],
    allow_overwrite=False
)
```

---

## Design Patterns

### Top-Level Agent Pattern

Each pipeline contains an intelligent DeepAgent that coordinates the workflow:

```python
from deepagents import create_deep_agent, CompiledSubAgent
from langgraph.checkpoint.memory import MemorySaver

def create_context_builder_agent(
    project_path: Path,
    *,
    allow_overwrite: bool = False
) -> Agent:
    """Create Context Builder top-level agent.

    Returns:
        DeepAgent: Intelligent coordinator for context enrichment.
    """
    # Load project context for tools
    context = await load_project_context(project_path)

    # Create stats tools for decision making
    stats_tools = [
        get_context_status,
        get_scene_completion,
        get_character_completion,
    ]

    # Create subagents (built with create_agent from langchain.agents)
    subagents = [
        create_scene_detailer_subagent(context, allow_overwrite=allow_overwrite),
        create_character_detailer_subagent(context, allow_overwrite=allow_overwrite),
        create_location_detailer_subagent(context, allow_overwrite=allow_overwrite),
        create_glossary_curator_subagent(context, allow_overwrite=allow_overwrite),
        create_route_detailer_subagent(context, allow_overwrite=allow_overwrite),
    ]

    # Create top-level DeepAgent
    return create_deep_agent(
        model="claude-sonnet-4-5-20250929",
        tools=stats_tools,
        system_prompt=CONTEXT_BUILDER_PROMPT,
        subagents=subagents,
        interrupt_on={
            # HITL for provenance violations
            "update_scene_summary": True,
            "update_character_notes": True,
            # ... other update tools
        },
        checkpointer=MemorySaver()
    )
```

**Key principles**:
- Top-level agent is **intelligent** - makes decisions, not just runs steps
- Uses **stats tools** to understand current state (NOT read tools)
- Spawns subagents via `task()` tool when work is needed
- Can **iterate** if results are insufficient
- Handles **HITL interrupts** for provenance violations

### Shared ProjectContext Management

rentl enforces **single-game-per-repo** with a **shared mutable ProjectContext** that all agents see.

**Critical implementation details:**

```python
async def create_context_builder_agent(project_path: Path) -> Agent:
    # 1. Load shared context ONCE
    context = await load_project_context(project_path)

    # 2. Pass same instance to ALL subagent factories
    subagents = [
        create_scene_detailer_subagent(context),  # Same context
        create_character_detailer_subagent(context),  # Same context
        create_glossary_curator_subagent(context),  # Same context
    ]

    # 3. Create stats tools (also need context via ToolRuntime)
    stats_tools = build_stats_tools()

    # 4. Middleware injects context into ToolRuntime
    class ContextMiddleware:
        async def before_agent(self, state, runtime):
            runtime.context.project_context = context
            runtime.context.project_path = project_path
            return {}

    # 5. Create top-level agent with middleware
    agent = create_deep_agent(
        model="claude-sonnet-4-5-20250929",
        tools=stats_tools,
        subagents=subagents,
        middleware=[ContextMiddleware()],  # Injects context
        interrupt_on={...},
        checkpointer=MemorySaver()
    )

    return agent
```

**How context flows:**
1. **Top-level agent loads** `ProjectContext` once from `project_path`
2. **Subagent factories receive** same context instance via parameter
3. **Subagent middleware injects** context into `runtime.context.project_context`
4. **Tools access** context via `runtime.context.project_context`
5. **All updates are immediate** - in-memory changes visible to all concurrent agents
6. **Writes are crash-safe** - each update persists to disk immediately

**Why this works:**
- ✅ **No stale data**: All agents see the same in-memory instance
- ✅ **Immediate visibility**: When one subagent updates, others see it instantly
- ✅ **Crash-safe**: Each update writes to disk before releasing lock
- ✅ **No confusion**: Single game per repo = single context instance
- ✅ **Thread-safe**: Entity-level locks prevent concurrent update conflicts

**Subagent factory pattern:**
```python
def create_scene_detailer_subagent(context: ProjectContext) -> CompiledSubAgent:
    """Create scene detailer with shared context."""
    tools = build_scene_tools()  # Generic tools, NOT scene-specific

    # Middleware injects SAME context instance into subagent runtime
    class SubagentContextMiddleware:
        async def before_agent(self, state, runtime):
            runtime.context.project_context = context  # Same instance!
            return {}

    graph = create_agent(
        model=get_default_chat_model(),
        tools=tools,
        middleware=[SubagentContextMiddleware()]
    )

    return CompiledSubAgent(
        name="scene-detailer",
        description="Enriches scene metadata",
        runnable=graph
    )
```

**Key: Tools are generic and accept scene_id as parameter:**
```python
@tool
async def update_scene_summary(scene_id: str, summary: str, runtime: ToolRuntime) -> str:
    """Update any scene's summary."""
    context = runtime.context.project_context  # Shared instance
    await context.update_scene_summary(scene_id, summary, origin="agent:scene_detailer")
    return f"Updated scene {scene_id}"
```

### Stats Tools for Top-Level Agents

Top-level agents need high-level visibility without context bloat:

```python
from langchain.tools import tool, ToolRuntime

@tool
def get_context_status(runtime: ToolRuntime) -> str:
    """Get overview of context building progress.

    Returns summary of completion across all metadata types.
    """
    context = runtime.context.project_context

    scenes_total = len(context.scenes)
    scenes_detailed = sum(1 for s in context.scenes.values() if s.annotations.summary)

    chars_total = len(context.characters)
    chars_detailed = sum(
        1 for c in context.characters.values()
        if c.name_tgt and c.pronouns and c.notes
    )

    locs_total = len(context.locations)
    locs_detailed = sum(
        1 for l in context.locations.values()
        if l.name_tgt and l.description
    )

    return f"""Context Status:
- Scenes: {scenes_detailed}/{scenes_total} detailed ({scenes_detailed/scenes_total*100:.1f}%)
- Characters: {chars_detailed}/{chars_total} detailed ({chars_detailed/chars_total*100:.1f}%)
- Locations: {locs_detailed}/{locs_total} detailed ({locs_detailed/locs_total*100:.1f}%)
- Glossary: {len(context.glossary)} entries
- Routes: {len(context.routes)} defined
"""

@tool
def get_translation_progress(scene_id: str, runtime: ToolRuntime) -> str:
    """Check translation progress for a scene."""
    project_path = runtime.context.project_path
    output_file = project_path / "output" / "translations" / f"{scene_id}.jsonl"

    if not output_file.exists():
        return f"Scene {scene_id}: Not translated"

    # Count translated lines
    with open(output_file) as f:
        lines = [line for line in f]

    return f"Scene {scene_id}: {len(lines)} lines translated"
```

**Critical:** Stats tools return aggregates, NOT full content. This prevents context bloat while giving the agent decision-making information.

### Intelligent Workflow Execution

Run independent subagents concurrently:

```python
async def run_context_builder(context: ProjectContext, scene_id: str):
    """Run all context builder subagents for a scene."""
    # These can run in parallel (independent tasks)
    async with anyio.create_task_group() as tg:
        tg.start_soon(scene_detailer, context, scene_id)
        tg.start_soon(detect_idioms, context, scene_id)
        tg.start_soon(detect_references, context, scene_id)

    # This runs after the parallel tasks complete
    await summarize_scene(context, scene_id)
```

**Why**: Independent analysis tasks (idiom detection, reference detection, summarization) can run concurrently. Scene translation must happen after context is built.

### Content-First, Not Line-First

**❌ Bad: Translate lines in isolation**

```python
# Don't do this—loses context!
async def translate_scene(lines: list[SourceLine]):
    translations = await asyncio.gather(*[
        translate_line(line.text) for line in lines
    ])
    return translations
```

**✅ Good: Translate scene with full context**

```python
async def translate_scene(context: ProjectContext, scene_id: str):
    # Load full scene context
    scene_meta = context.get_scene(scene_id)
    lines = await context.load_scene_lines(scene_id)
    characters = [context.get_character(cid) for cid in scene_meta.annotations.primary_characters]
    glossary = context.glossary

    # Translate with full scene + metadata context
    translations = await scene_translator(
        lines=lines,
        characters=characters,
        glossary=glossary,
        style_guide=await context.read_context_doc("style_guide.md")
    )
    return translations
```

### Error Handling and Retries

Retry transient errors, fail fast on configuration errors:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(TransientError)
)
async def call_subagent(subagent_fn, *args):
    """Call subagent with retry on transient errors."""
    try:
        return await subagent_fn(*args)
    except RateLimitError:
        raise TransientError("Rate limit hit")
    except NetworkError:
        raise TransientError("Network timeout")
    except ConfigurationError:
        raise  # Don't retry config errors—fail fast
```

**Guidelines**:
- **Retry**: Rate limits, network timeouts, temporary service outages
- **Fail fast**: Missing API keys, invalid models, file not found errors

### Progress Reporting

Report progress for long-running pipelines:

```python
async def run_context_pipeline(
    context: ProjectContext,
    scene_ids: list[str],
    progress_callback: Callable[[str, int, int], None] | None = None
):
    """Run context building for multiple scenes with progress reporting."""
    results = []

    for i, scene_id in enumerate(scene_ids, start=1):
        if progress_callback:
            progress_callback(scene_id, i, len(scene_ids))

        result = await run_context_builder(context, scene_id)
        results.append(result)

    return results
```

Usage in CLI:

```python
def progress_callback(scene_id: str, current: int, total: int):
    print(f"Processing {scene_id} ({current}/{total})")

await run_context_pipeline(context, scenes, progress_callback=progress_callback)
```

---

## Testing Guidelines

### Unit Tests

Test individual pipeline stages with mocked subagents:

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_context_pipeline():
    context = await load_project_context(Path("examples/tiny_vn"))

    # Mock subagent calls
    mock_detailer = AsyncMock(return_value="Summary")

    result = await run_context_builder(
        context,
        "scene_c_00",
        scene_detailer=mock_detailer
    )

    assert result.scene_id == "scene_c_00"
    mock_detailer.assert_called_once()
```

### Integration Tests

Test full pipeline with lightweight LLM:

```python
@pytest.mark.asyncio
async def test_full_pipeline():
    context = await load_project_context(Path("examples/tiny_vn"))

    # Use mocked or lightweight LLM
    result = await run_scene_pipeline(context, "scene_c_00")

    # Verify outputs
    assert result.scene_id == "scene_c_00"
    assert result.summary is not None
    assert result.translation_path.exists()
    assert len(result.qa_checks) > 0
```

---

## Best Practices

### DO

- ✅ Use async/await throughout
- ✅ Run independent tasks in parallel with `anyio.create_task_group()`
- ✅ Retry transient errors with exponential backoff
- ✅ Fail fast on configuration errors
- ✅ Pass full scene context to translators (not isolated lines)
- ✅ Report progress for long-running operations
- ✅ Keep pipelines focused—delegate to subagents for actual work

### DON'T

- ❌ Don't translate lines in isolation (loses context)
- ❌ Don't retry configuration errors (fail fast instead)
- ❌ Don't implement subagent logic in pipelines (keep them in `rentl-agents`)
- ❌ Don't block the event loop with synchronous I/O
- ❌ Don't ignore errors—handle or propagate them clearly

---

## Common Patterns

### Running Multiple Scenes

```python
from rentl_pipelines.runner import run_context_pipeline

async def main():
    context = await load_project_context(Path("game_project"))

    # Run context building for all scenes
    results = await run_context_pipeline(
        context,
        scenes=["scene_c_00", "scene_a_00", "scene_r_00"],
        allow_overwrite=False
    )

    # Check results
    for result in results:
        print(f"{result.scene_id}: {result.summary}")
```

### Handling Errors Gracefully

```python
async def run_pipeline_with_error_handling(context, scenes):
    results = []
    errors = []

    for scene_id in scenes:
        try:
            result = await run_scene_pipeline(context, scene_id)
            results.append(result)
        except ConfigurationError as e:
            # Fatal error—stop processing
            raise
        except Exception as e:
            # Log and continue with other scenes
            errors.append((scene_id, str(e)))
            continue

    return results, errors
```

---

## Future Patterns (v1.1+)

### Route-Level Pipeline

Process all scenes in a route together for consistency:

```python
async def run_route_pipeline(context: ProjectContext, route_id: str):
    """Process all scenes in a route with cross-scene consistency checks."""
    route = context.get_route(route_id)

    # Phase 1: Context building (parallel across scenes)
    async with anyio.create_task_group() as tg:
        for scene_id in route.scene_ids:
            tg.start_soon(run_context_builder, context, scene_id)

    # Phase 2: Translation (sequential with context from previous scenes)
    translations = []
    for scene_id in route.scene_ids:
        trans = await run_translator(context, scene_id, prior_scenes=translations)
        translations.append(trans)

    # Phase 3: Cross-scene consistency checks
    await check_route_consistency(context, route_id, translations)
```

### Multi-Pass Game Pipeline

Run multiple passes over the entire game:

```python
async def run_game_pipeline(context: ProjectContext):
    """Multi-pass pipeline for full game."""
    # Pass 1: Context building (all scenes)
    await run_context_pipeline(context, context.scenes.keys())

    # Pass 2: Translation (all scenes)
    await run_translation_pipeline(context, context.scenes.keys())

    # Pass 3: Cross-scene consistency
    await run_consistency_checks(context)

    # Pass 4: Editing and QA
    await run_editing_pipeline(context, context.scenes.keys())
```

---

## Dependencies

**Required**:
- `rentl-core`: Data models, I/O, project context
- `rentl-agents`: Subagent implementations
- `anyio`: Async task groups
- `tenacity`: Retry logic

**No CLI dependencies**: Pipelines should be usable programmatically without CLI.

---

## Summary

`rentl-pipelines` orchestrates the translation workflow by:
- Coordinating subagents in the right order
- Running independent tasks in parallel
- Handling errors gracefully
- Reporting progress

**Key principle**: Pipelines orchestrate; subagents do the actual work.

See [AGENTS.md](../../AGENTS.md) for performance and concurrency guidelines.
