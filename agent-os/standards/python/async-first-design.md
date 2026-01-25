# Async-First Design

Design all APIs and I/O around `async`/`await` and modern structured concurrency.

```python
# ✓ Good: Async-first API
from pydantic import BaseModel

class TranslationRequest(BaseModel):
    scenes: list[str]

async def translate_scenes(request: TranslationRequest) -> list[str]:
    """Translate scenes in parallel using structured concurrency."""
    tasks = [translate_scene(scene) for scene in request.scenes]
    return await asyncio.gather(*tasks)

async def translate_scene(scene: str) -> str:
    """Translate single scene - async for LLM network IO."""
    ...

# ✗ Bad: Blocking I/O
def translate_scenes(request: TranslationRequest) -> list[str]:
    """Translate scenes sequentially - blocks on network IO."""
    results = []
    for scene in request.scenes:
        results.append(translate_scene_sync(scene))  # Blocks
    return results
```

**Why async-first matters:**
- **Parallel execution**: Many phases run agents in parallel (same agent on many scenes at once)
- **Network IO efficiency**: Vast compute requirement is network IO to LLMs; async handles this efficiently
- **Scalability**: Avoid blocking on slow external services
- **Resource efficiency**: Single thread can handle many concurrent network calls

**Async requirements:**
- All I/O operations (LLM calls, storage, vector store, file IO) use `async`/`await`
- Design APIs to be callable from async contexts
- Use modern structured concurrency (`asyncio.gather`, `asyncio.TaskGroup`, etc.)
- Avoid blocking operations in async paths

**Exceptions (entry points only):**
- Script entry points (`main`, CLI commands) may use synchronous wrappers
- Must bridge to async code immediately (e.g., `asyncio.run()`)
- Never block inside async functions

**Why async-first:** Enables parallel execution of agents/scenes, handles network IO to LLMs efficiently, and scales without blocking on slow external services.
