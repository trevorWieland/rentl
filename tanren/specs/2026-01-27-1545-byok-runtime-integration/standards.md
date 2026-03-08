# Standards for BYOK Runtime Integration

The following standards apply to this work.

---

## testing/make-all-gate

# Make All Gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands

---

## python/async-first-design

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

---

## python/modern-python-314

# Modern Python 3.14

Use Python 3.14 features and patterns. Avoid legacy constructs.

```python
# ✓ Good: Modern Python 3.14
# Type unions (Python 3.10+)
result: str | None

# Pattern matching (Python 3.10+)
match phase:
    case "translate":
        await translate()
    case "qa":
        await run_qa()
    case _:
        raise ValueError(f"Unknown phase: {phase}")

# Dictionary union operators (Python 3.9+)
config = base_config | custom_config

# f-string debugging (Python 3.8+)
print(f"{result=}")  # Prints: result='value'

# Async generators (Python 3.6+)
async def stream_translations():
    for scene in scenes:
        yield await translate_scene(scene)

# ✗ Bad: Legacy patterns
result: Optional[str]  # Old-style Union

if phase == "translate":
    await translate()
elif phase == "qa":
    await run_qa()
else:
    raise ValueError(f"Unknown phase: {phase}")  # No pattern matching

config = {**base_config, **custom_config}  # Old unpacking

print(f"result={result}")  # No f-string debugging

def stream_translations():  # Blocking generator
    for scene in scenes:
        yield translate_scene(scene)
```

**Modern Python 3.14 features to use:**
- Type unions: `str | None` instead of `Union[str, None]`
- Pattern matching: `match/case` instead of if/elif chains
- Dictionary union: `dict1 | dict2` instead of unpacking
- f-string debugging: `f"{var=}"` instead of `f"var={var}"`
- Walrus operator: `if (match := pattern.search(text)):` for assignment in expressions
- Async generators: `async def` and `async for`
- Context managers: `with` statements for resource management
- Dataclass improvements: `dataclass_transform` and field parameters

**Legacy patterns to avoid:**
- `Optional[T]`, `Union[T, U]` - use `T | None`, `T | U`
- `if/elif/else` chains for type/state - use `match/case`
- `{**d1, **d2}` - use `d1 | d2`
- `f"var={var}"` - use `f"{var=}"`
- `typing.List`, `typing.Dict` - use built-in `list`, `dict`
- `yield` without `async` - use async generators where appropriate

**Why:** Cleaner syntax, better expressiveness, fewer lines of code, performance improvements, optimized standard library features, and avoids learning outdated patterns.

---

## python/strict-typing-enforcement

# Strict Typing Enforcement

Never use `Any` or `object` in types. Always model explicit schema types.

```python
# ✓ Good: Explicit types
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str
    target_language: str
    model: str = Field(..., description="Model identifier for translation")

def translate(request: TranslationRequest) -> TranslationResult:
    """Translate with explicit types - ty will catch errors."""
    ...

# ✗ Bad: Any or object
from typing import Any

def translate(request: Any) -> Any:
    """Translate with Any - no type safety."""
    ...
```

**Type configuration:**
- `ty` must be configured in **strict mode**
- Type checking must pass with zero errors before merging
- All schemas, agents, tools, and APIs use explicit types

**Pydantic fields:**
- Every Pydantic field must use `Field(..., description="...")` with a clear description
- Use built-in validators (`min_length`, `max_length`, `pattern`, `gt`, `ge`, `lt`, `le`, etc.) for validation
- Never use raw type annotation without Field for schema fields

```python
# ✓ Good: Field with description and validators
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(..., pattern=r'^[a-z]{2}$', description="ISO 639-1 language code")
    model: str = Field(..., description="Model identifier for translation")

# ✗ Bad: Raw type annotation without Field
from pydantic import BaseModel

class TranslationRequest(BaseModel):
    source_text: str  # No description, no validators
    target_language: str
    model: str
```

**Exceptions (extremely rare, high bar):**
`Any` or `object` only when **all** are true:
1. Fully external library/API
2. Creating types isn't practical
3. No better alternative library or API exists
4. We actually need the feature and cannot avoid it

**Never** use `Any` for internal code, schema definitions, or where types are available.

**Why:** Catches type errors at dev time instead of runtime, makes code more readable and self-documenting, and prevents whole classes of bugs before they happen.

---

## architecture/thin-adapter-pattern

# Thin Adapter Pattern

Surface layers (CLI, TUI, API, etc.) are **thin adapters only**. All business logic lives in the **Core Domain** packages.

```python
# ✓ Good: CLI is a thin wrapper
def run_pipeline(run_id: str):
    """Start pipeline run - thin adapter over core API."""
    # Calls Core Domain API directly
    result = await pipeline_runner.start_run(run_id)
    return format_json_output(result)

# ✗ Bad: Business logic in CLI
def run_pipeline(run_id: str):
    """Start pipeline run - contains core logic."""
    validate_config(config)  # Business logic
    context = build_context(sources)  # Business logic
    result = translate(context)  # Business logic
    return result
```

**Core Domain logic includes:**
- Pipeline orchestration and phase execution
- Data transformation and validation
- Agent orchestration
- Storage operations
- Model integration

**Surface layers may contain:**
- Command definitions and argument parsing
- Output formatting (pretty-print, JSON wrapper)
- Truly surface-specific features that will never be reused

**Even validation and formatting should use contract models from the Core Domain** - never duplicate schemas or business rules.

**Why:** Ensures core logic is reusable across any surface (CLI, TUI, API, Lambda) without duplication and makes testing easier (test core once, surfaces are just IO wrappers).

---

## architecture/adapter-interface-protocol

# Adapter Interface Protocol

Never access infrastructure adapters directly. Always access storage, models, and external services through **Protocol Interfaces** defined in the Core Domain packages.

```python
# ✓ Good: Access through protocol interface
from core.adapters.vector import VectorStoreProtocol

async def search_context(query: str, vector_store: VectorStoreProtocol):
    """Search vector context via protocol - implementation agnostic."""
    return await vector_store.search(query)

# ✗ Bad: Direct access to implementation
import chromadb

async def search_context(query: str):
    """Search vector context - hardcoded to Chroma."""
    client = chromadb.Client()
    collection = client.get_collection("context")
    return collection.query(query)
```

**Pattern Structure:**
1.  **Define Protocol**: `core.ports.VectorStoreProtocol` (The contract)
2.  **Implement Adapter**: `infrastructure.adapters.chroma.ChromaVectorStore` (The specific tech)
3.  **Inject Dependency**: Pass the adapter where the protocol is expected

**Common Protocols:**
- `VectorStoreProtocol` - Vector storage and retrieval
- `ModelClientProtocol` - LLM model integration
- `StorageProtocol` - Metadata and artifact storage

**Access pattern:**
1.  Define protocol interface in the Core Domain (Ports)
2.  Provide implementation in an Infrastructure package (Adapters)
3.  Inject protocol dependency at runtime
4.  Use only protocol methods - never concrete class

**Why:** Enables swapping implementations (Chroma -> pgvector, OpenAI -> local models) without changing business logic, makes testing easier with mock protocols, and keeps the core domain clean of infrastructure concerns (Hexagonal/Clean Architecture).

---

## ux/trust-through-transparency

# Trust Through Transparency

No silent stalls, no black boxes. Every phase, error, and status must be visible and explainable.

```python
# ✓ Good: Transparent, explainable behavior
async def translate_phase(config: Config) -> TranslationResult:
    """Translate phase with full visibility."""
    # Show what's happening
    await emit_event("phase_started", {
        "phase": "translate",
        "model": config.model,
        "scenes_to_process": len(config.scenes)
    })
    
    # Progress updates (not silent)
    for i, scene in enumerate(config.scenes):
        await emit_event("translation_progress", {
            "scene_id": scene.id,
            "line_number": i + 1,
            "total_lines": len(config.scenes)
        })
        result = await translate_single(scene, config)
        await emit_event("translation_completed", {
            "scene_id": scene.id,
            "status": "success",
            "tokens_used": result.tokens_used
        })
    
    # Show what happened, even on error
    except TranslationError as e:
        await emit_event("translation_failed", {
            "scene_id": scene.id,
            "error_code": e.code,
            "error_message": e.message,
            "retries_attempted": e.retries,
            "next_action": "Will retry with smaller context"
        })
        raise  # Re-raise but visibility is already emitted

# ✓ Good: Error messages explain what happened and why
Error: Translation failed for scene 42
Code: RATE_LIMIT
Details: API rate limit exceeded (100 req/min). Retrying in 30s...
Phase: translate
Scene ID: 42
Retry count: 1 of 3

# ✗ Bad: Silent or opaque behavior
async def translate_phase(config: Config) -> TranslationResult:
    """Translate phase - no visibility."""
    # No progress events
    results = []
    for scene in config.scenes:
        results.append(await translate_single(scene, config))  # Silent
    
    # No visibility into what happened
    except Exception as e:
        raise e  # Re-raise with no context

# ✗ Bad: Opaque error messages
Error: Translation failed
[No code, no details, no explanation of what went wrong]
```

**Transparency requirements:**
- **Phase visibility:** Always show phase start, progress, and completion
- **Error visibility:** Never fail silently; always emit error with context and next action
- **Progress visibility:** Show progress within phases, not just at phase boundaries
- **Status explainability:** Every status change has a reason or context

**Error messages must include:**
- **What happened:** Clear description of the failure
- **Why it happened:** Error code or context (e.g., rate limit, invalid config)
- **What's next:** Recovery action or next step (retrying, skipping, user intervention needed)
- **Phase context:** Which phase failed, which line/scene

**Progress visibility:**
- Emit events at meaningful milestones (every N lines, scene completions, etc.)
- Show what's being processed (line IDs, scene names, file paths)
- Show time elapsed and ETA for long operations
- Don't batch updates - emit as work progresses

**Never:**
- Silent failures (exception without context)
- Opaque error messages (generic "failed" without explanation)
- Long-running operations without progress (e.g., "waiting..." for >5 seconds)
- Hidden retries (don't retry 3 times silently; show each attempt)

**Why:** Users know if pipeline is working or stuck; failures and errors are visible and explainable; builds confidence in system behavior.

---

## ux/frictionless-by-default

# Frictionless by Default

Guided CLI + safe defaults make first run feel effortless. Users should succeed without reading docs or expert knowledge.

```python
# ✓ Good: Guided setup with safe defaults
async def init_command(project_dir: str) -> None:
    """Initialize project with guided setup."""
    # Step 1: Detect game type (with default)
    game_type = await detect_game_type(project_dir)
    if game_type is None:
        game_type = await ask_user(
            "What game engine are you translating?",
            options=["RPG Maker", "Ren'Py", "Kirikiri", "Other"],
            default="Ren'Py"  # Safe default
        )
    
    # Step 2: Suggest config with safe defaults
    config = generate_config_with_defaults(game_type)
    print(f"Generated config for {game_type} with:")
    print(f"  - Model: {config.model} (safe default)")
    print(f"  - Language: {config.target_language} (detect from files or ask)")
    
    # Step 3: Validate before proceeding
    if not await validate_config(config):
        print("Config needs adjustment. Let's fix:")
        config = await guided_config_fix(config)
    
    save_config(config)
    print("✓ Project initialized. Run 'rentl run-pipeline' to start.")

# ✓ Good: CLI with defaults and guided flow
$ rentl init
Detected game engine: Ren'Py
Suggested config:
  - Model: gpt-4o-mini (recommended for speed/cost)
  - Target language: English (detected from project)
  - Source files: ./src/scripts.rpy (auto-detected)

Accept defaults? [Y/n]: Y
✓ Config saved to rentl.toml

# ✗ Bad: Manual configuration without guidance
async def init_command(project_dir: str) -> None:
    """Initialize project - manual configuration required."""
    print("Create rentl.toml manually. See docs for all options.")
    print("Required fields: model, api_key, source, target, phases...")
    # User must read docs to understand all required fields
    # No defaults, no guidance, no validation
    # High friction for first-time users
```

**Guided setup requirements:**
- **Interactive init:** Ask questions with sensible defaults when auto-detection fails
- **Auto-detection:** Detect game engine, source files, language from project structure
- **Safe defaults:** Provide defaults that work for most common use cases
- **Validation:** Validate config before accepting; fix issues interactively
- **Next steps:** Always tell user what to do next

**Default behavior:**
- **Model:** Recommend cost-effective default (e.g., gpt-4o-mini for translation speed)
- **Language:** Detect from project or files; default to English if unclear
- **Source paths:** Auto-detect common patterns (scripts/, src/, data/)
- **Phase selection:** Enable all phases by default; let user opt-out if needed
- **Concurrency:** Default to safe parallelism (e.g., 3-5 concurrent requests)

**Configuration flow:**
1. Auto-detect what's possible (game engine, files, language)
2. Ask for missing info with safe defaults pre-filled
3. Show what will be configured before accepting
4. Validate config and fix issues interactively
5. Save and show next steps

**Exceptions (non-standard workflows):**
Only when non-standard workflow requires customization beyond defaults (e.g., custom engine adapters, specialized QA rules), prompt user for configuration but still provide reasonable defaults.

**Why:** First run succeeds without reading docs or expert knowledge; reduces onboarding friction for lightly technical users; creates positive "already?" moment when pipeline works immediately.

---

## testing/three-tier-test-structure

# Three-Tier Test Structure

All tests live under `tests/unit`, `tests/integration`, or `tests/quality`. No exceptions.

```
tests/
├── unit/           # <250ms per test, mocks only, no external services
│   ├── core/
│   ├── cli/
│   └── tui/
├── integration/    # <5s per test, minimal mocks, real services, NO LLMs
│   ├── core/
│   ├── cli/
│   └── tui/
└── quality/        # <30s per test, minimal mocks, real services, REAL LLMs
    ├── core/
    └── cli/
```

**Tier definitions:**

**Unit tests** (`tests/unit/`):
- Fast: <250ms per test
- Mocks allowed and encouraged
- No external services (no network, no LLMs, no databases)
- Test isolated logic and algorithms

**Integration tests** (`tests/integration/`):
- Moderate speed: <5s per test
- Minimal mocks (only when unavoidable)
- Real services (storage, vector store, file system)
- **NO LLMs** - use mock model adapters for LLM calls
- BDD-style (Given/When/Then)

**Quality tests** (`tests/quality/`):
- Slower but bounded: <30s per test
- Minimal mocks (only when unavoidable)
- Real services (storage, vector store, file system)
- **REAL LLMs** - actual model calls, not mocked
- BDD-style (Given/When/Then)

**Package structure mirrors source:**
- `tests/unit/core/` tests `rentl_core/`
- `tests/integration/cli/` tests `rentl_cli/`
- Etc.

**Never place tests:**
- Outside the three tier folders
- In source code directories
- In ad-hoc locations (scripts, benchmarks, etc.)

**CI execution:**
- Unit tests: Run on every PR, fast feedback
- Integration tests: Run on every PR or schedule
- Quality tests: Run on schedule or manual trigger (slower)

**Why:** Clear purpose and scope for each test tier, and enables selective execution by tier (unit fast/run frequently, integration/quality slower/run selectively).

---

## testing/no-mocks-for-quality-tests

# No Mocks for Quality Tests

Quality tests use real LLMs (actual model calls). Integration tests must mock LLMs.

```python
# ✓ Good: Quality test with real LLM
# tests/quality/core/translation.py
from rentl_core.adapters.model.openai_client import OpenAIClient

async def test_translation_quality_with_real_llm(given_translation_request):
    """Test translation quality with actual model call."""
    client = OpenAIClient(base_url="https://api.openai.com/v1", api_key="test-key")
    result = await client.translate(given_translation_request)

    # Validate actual model output, not mocked response
    assert result.text is not None
    assert len(result.text) > 0
    assert result.model == "gpt-4"

# ✓ Good: Integration test with mocked LLM
# tests/integration/core/translation.py
from unittest.mock import AsyncMock

async def test_translation_flow(given_translation_request):
    """Test translation flow with mocked LLM (no real calls)."""
    mock_client = AsyncMock()
    mock_client.translate.return_value = TranslationResult(text="mocked text", model="gpt-4")

    result = await mock_client.translate(given_translation_request)
    assert result.text == "mocked text"  # Verify mock, not real model

# ✗ Bad: Quality test with mocked LLM
async def test_translation_quality(given_translation_request):
    """Quality test must NOT mock LLM."""
    mock_client = AsyncMock()
    mock_client.translate.return_value = TranslationResult(text="mocked text")
    # This validates mock, not real model behavior - FAILS QA PURPOSE
```

**Quality tests:**
- **REAL LLMs** - actual model calls, not mocked
- BDD-style (Given/When/Then)
- Real services (storage, vector store, file system)
- Minimal mocks (only when unavoidable)
- <30s per test
- Validates actual model behavior and quality, not mocked responses

**Integration tests:**
- **NO LLMs** - mock model adapters for LLM calls
- BDD-style (Given/When/Then)
- Real services (storage, vector store, file system)
- Minimal mocks (only when unavoidable)
- <5s per test
- Tests pipeline flow, not model behavior

**Why real LLMs in quality tests:**
- Validates actual model behavior and quality
- Catches regressions when models change or update
- Ensures prompts and schemas work with real models
- Tests error handling for real API responses

**Why mock LLMs in integration tests:**
- Fast feedback (<5s vs <30s)
- Avoids LLM API rate limits and costs
- Tests pipeline flow, not model behavior
- Makes integration tests deterministic and fast

**Never mock LLMs for:**
- Quality tests (defeats purpose)
- Validating model-specific behavior
- Testing prompt engineering effectiveness
- Validating actual translation quality

**Never use real LLMs for:**
- Unit tests (should be <250ms)
- Integration tests (should be <5s)

**API key management for quality tests:**
- Use test API keys with rate limits
- Cache LLM responses when possible (within <30s bound)
- Document API key setup in test docs
- CI should have API key configured for quality tier

**Why:** Validates actual model behavior and quality, not mocked responses; ensures prompts and schemas work with real models and tests error handling for real API responses.
