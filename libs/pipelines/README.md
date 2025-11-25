# rentl-pipelines: Phase Pipelines

Deterministic, phase-first pipelines that schedule LangChain subagents for context building, translation, pretranslation, and editing/QA. No LLM “coordinator” agents—pipelines are regular Python flows with queues, bounded concurrency, and human-in-the-loop pauses.

---

## Purpose

`rentl-pipelines` provides **phase runners** that:

- Build work queues from project state (e.g., incomplete scenes, untranslated scenes, QA-needed scenes)
- Schedule LangChain subagents with bounded concurrency
- Handle retries and HITL pauses (via LangChain middleware + checkpointers)
- Collect and report results for CLI/TUI dashboards

**Not responsible for**:
- Individual subagent logic (belongs in `rentl-agents`)
- Data models or I/O (belongs in `rentl-core`)
- CLI/TUI interface (belongs in `rentl-cli` and future Textual UI)

---

## Architecture

### Pipelines (This Package)

- **Context pipeline**: runs scene/character/location/route/glossary detailers over incomplete entities; supports overwrite, gap-fill, or new-only modes.
- **Translator pipeline**: runs scene translators for targeted scenes; respects overwrite flags and progress checks.
- **Editor/QA pipeline**: runs style/consistency/reviewer subagents on translated scenes.
- **Pretranslation (v1.1)**: planned phase for idioms/references/accent profiling.

### Subagents (rentl-agents Package)

Subagents are specialized LangChain agents:
- Work in isolated context; only see specialized tools
- Use HITL middleware as needed (`HumanInTheLoopMiddleware` + checkpointer)
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

- flows/context_builder.py
- flows/translator.py
- flows/editor.py

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

### Pipeline Pattern

Each pipeline is a deterministic async flow:

```python
async def run_context_pipeline(project_path: Path, *, allow_overwrite: bool = False):
    context = await load_project_context(project_path)

    # Compute queues from state
    pending_scenes = [sid for sid, scene in context.scenes.items() if not scene.annotations.summary]

    # Run subagents directly; replace with bounded concurrency when ready
    for sid in pending_scenes:
        await detail_scene(context, sid, allow_overwrite=allow_overwrite)

    return {"scenes_detailed": len(pending_scenes)}
```

**Key principles**:
- Pipelines are **deterministic**: queues are derived from on-disk state
- Concurrency should be bounded (anyio task groups) when added
- HITL pauses come from LangChain middleware + checkpointers on subagents
- Progress is recomputed on each run; reruns naturally resume

### Shared ProjectContext Management

rentl enforces **single-game-per-repo** with a **shared mutable ProjectContext** that all subagents see. Pipelines load it once, subagents receive it via middleware, tools do all I/O, and updates persist immediately with locks and conflict feedback.

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
