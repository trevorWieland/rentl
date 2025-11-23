# rentl-pipelines: Orchestration Workflows

Async workflows that coordinate subagents across scenes, routes, and entire game projects.

---

## Purpose

`rentl-pipelines` orchestrates the translation workflow by:

- Coordinating multiple subagents in sequence or parallel
- Managing scene-level, route-level, and game-level processing
- Handling errors and retries
- Collecting and reporting results

**Not responsible for**:
- Individual subagent logic (belongs in `rentl-agents`)
- Data models or I/O (belongs in `rentl-core`)
- CLI interface (belongs in `rentl-cli`)

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

### Scene-Level Pipeline (v1.0)

Process one scene at a time through the full workflow:

```python
async def run_scene_pipeline(
    context: ProjectContext,
    scene_id: str,
    allow_overwrite: bool = False
) -> SceneResult:
    """Run full pipeline for a single scene.

    Phases:
    1. Context Building (enrich metadata)
    2. Translation (produce target text)
    3. Editing (QA checks, flag issues)

    Args:
        context: Project context with metadata.
        scene_id: Scene identifier.
        allow_overwrite: Whether to overwrite existing data.

    Returns:
        Results with summaries, translations, QA checks.
    """
    # Phase 1: Context Building
    await run_context_builder(context, scene_id, allow_overwrite)

    # Phase 2: Translation
    await run_translator(context, scene_id)

    # Phase 3: Editing
    qa_results = await run_editor(context, scene_id)

    return SceneResult(
        scene_id=scene_id,
        summary=context.get_scene(scene_id).annotations.summary,
        translation_path=f"output/translations/{scene_id}.jsonl",
        qa_checks=qa_results
    )
```

**Key principles**:
- Each phase is **async** and can be run independently
- Phases run **sequentially** (context → translate → edit)
- Within a phase, **subagents may run in parallel** (task-level parallelism)

### Task-Level Parallelism

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
