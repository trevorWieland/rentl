# Standards for Phase Result Summaries & Metrics

The following standards apply to this work.

---

## architecture/log-line-format

# Log Line Format

All log lines use stable JSONL schema with `{timestamp, level, event, run_id, phase, message, data}` fields.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

# ✓ Good: Stable Pydantic model for log lines
class LogEntry(BaseModel):
    """Single log line in JSONL format."""
    timestamp: str = Field(..., description="ISO-8601 timestamp")
    level: Literal["debug", "info", "warn", "error"] = Field(
        ..., description="Log level"
    )
    event: str = Field(..., description="Event type (e.g., run_started, phase_completed)")
    run_id: str = Field(..., description="Pipeline run identifier")
    phase: str | None = Field(None, description="Pipeline phase (e.g., translate, qa)")
    message: str = Field(..., description="Human-readable log message")
    data: dict | None = Field(None, description="Structured event data")

# ✓ Good: Writing log lines
def write_log(entry: LogEntry) -> None:
    """Write log line to JSONL file."""
    with open("logs/pipeline.log", "a") as f:
        f.write(entry.model_dump_json() + "\n")
```

```json
// ✓ Good: Log line examples
{"timestamp":"2026-01-23T12:00:00Z","level":"info","event":"run_started","run_id":"abc123","phase":null,"message":"Pipeline started","data":{"config_file":"rentl.toml"}}
{"timestamp":"2026-01-23T12:01:00Z","level":"info","event":"phase_completed","run_id":"abc123","phase":"translate","message":"Translation phase completed","data":{"lines_translated":1234,"duration_s":45.2}}
{"timestamp":"2026-01-23T12:02:00Z","level":"error","event":"translation_failed","run_id":"abc123","phase":"translate","message":"Translation failed for scene 42","data":{"scene_id":42,"error_code":"RATE_LIMIT","retry_count":3}}
```

**Log line Pydantic model requirements:**
- `timestamp`: ISO-8601 timestamp string (required)
- `level`: One of `debug`, `info`, `warn`, `error` (required)
- `event`: Event name in `snake_case` (required)
- `run_id`: Pipeline run identifier (required)
- `phase`: Pipeline phase name or `None` (optional)
- `message`: Human-readable log message (required)
- `data`: Structured event data as dict or `None` (optional)

**JSONL format:**
- One JSON object per line
- Lines separated by newlines
- No outer array or object wrapper
- UTF-8 encoding

**Event naming conventions:**
- Use `snake_case` for event names
- Examples: `run_started`, `phase_completed`, `translation_finished`, `error_occurred`
- Prefix with phase name when applicable: `translate_completed`, `qa_failed`

**Level usage guidelines:**
- `debug`: Detailed diagnostics for development
- `info`: Normal operational messages (phase starts/completions)
- `warn`: Recoverable issues (retries, fallbacks)
- `error`: Failures requiring attention

**Exceptions (external logging systems):**
When integrating with external logging systems (e.g., cloud logging services, ELK stacks), follow their schema requirements but map required fields where possible.

**Why:** Consistent log parsing for observability tools and dashboards; enables easy log analysis and filtering; structured data is machine-readable and queryable.

---

## architecture/none-vs-empty

# None vs Empty Lists

Use `None` to mean "not provided." Use `[]` to mean "provided but empty."

Rules:
- Optional list fields default to `None`
- If a phase runs and produces no items, return `[]`
- Do not omit required list fields; pass an empty list if there are no items

---

## architecture/naming-conventions

# Naming Conventions

Use consistent naming conventions across all code. Never mix styles.

```python
# ✓ Good: Consistent snake_case for modules/functions/variables
from translation_engine import translate_scene
from config_loader import load_config

def process_scene(scene: Scene) -> TranslationResult:
    """Process single scene."""
    result = translate_scene(scene)
    return result

# ✓ Good: PascalCase for classes/types
class TranslationRequest(BaseModel):
    """Translation request model."""

class VectorStoreProtocol(Protocol):
    """Vector store interface protocol."""

class SQLiteIndex:
    """SQLite run metadata index."""

# ✗ Bad: Inconsistent naming
from TranslationEngine import translate_Scene  # PascalCase for module
from config_loader import LoadConfig  # PascalCase for function

def ProcessScene(scene: Scene) -> TranslationResult:  # PascalCase for function
    ...

class translationRequest:  # snake_case for class
    pass
```

**Python code naming:**
- Modules/files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes/types: `PascalCase`

**Database naming:**
- Tables/collections: `snake_case`
- Columns/fields: `snake_case`
- Foreign keys: `{entity}_id` (e.g., `run_id`, `scene_id`)

**API naming:**
- CLI commands: `kebab-case` (e.g., `run-pipeline`, `show-status`)
- CLI options: `--snake-case` (e.g., `--run-id`, `--config-file`)

**JSON/JSONL naming:**
- Fields: `snake_case` (e.g., `run_id`, `phase_name`, `error_message`)

**Event naming:**
- Event names: `snake_case` (e.g., `run_started`, `phase_completed`, `translation_finished`)
- Log event names (JSONL `event`) must be `snake_case`
- When phase-specific, prefix with phase name (e.g., `translate_completed`, `qa_failed`)

**Why:** Consistency makes code predictable and easier to navigate; reduces confusion when multiple developers/agents work together.

---

## architecture/id-formats

# ID Formats

Use UUIDv7 for internal, non-human IDs. Use `{word}_{number}` for human-readable IDs.

Examples:
- UUIDv7: `01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0`
- Human: `line_42`, `scene_7`, `run_3`

Rules:
- Internal IDs (runs, artifacts, notes, issues) must be UUIDv7
- Human-readable IDs (line_id, scene_id) must match `{word}_{number}`
- External engine IDs should be mapped to internal IDs and stored in metadata

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

## python/pydantic-only-schemas

# Pydantic-Only Schemas

Never use dataclasses or plain classes for schemas. All schemas must use Pydantic.

```python
# ✓ Good: Pydantic schema
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(..., pattern=r'^[a-z]{2}$', description="ISO 639-1 language code")

# ✗ Bad: dataclass
from dataclasses import dataclass

@dataclass
class TranslationRequest:
    source_text: str  # No validation, no serialization
    target_language: str

# ✗ Bad: Plain class
class TranslationRequest:
    def __init__(self, source_text: str, target_language: str):
        self.source_text = source_text
        self.target_language = target_language
```

**When to use Pydantic schemas:**
- API request/response models
- Configuration models
- Agent input/output schemas
- Storage document models
- Any data that crosses package boundaries

**Pydantic requirements:**
- All fields use `Field(..., description="...")` with clear description
- Use built-in validators for validation (min_length, max_length, pattern, etc.)
- Inherit from `BaseModel` or appropriate Pydantic base
- Type-safe with full type annotations

**Never use dataclasses or plain classes for:**
- Schemas that serialize/deserialize
- Data that requires validation
- Configuration models
- API contracts

**Why:** Pydantic provides automatic validation, native JSON serialization/deserialization, better type inference and IDE support than dataclasses, and catches schema errors early.

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

## ux/progress-is-product

# Progress is the Product

Status, phase completion, and QA visibility must be immediate and unambiguous. Progress is the product, not a feature.

```python
# ✓ Good: Immediate, unambiguous progress updates
async def run_pipeline(run_id: str) -> None:
    """Run pipeline with visible progress."""
    # Phase 1: Ingest
    await emit_event("phase_started", {"phase": "ingest", "status": "running"})
    await ingest_phases(config)
    await emit_event("phase_completed", {"phase": "ingest", "lines": 1234, "duration_s": 2.3})
    
    # Phase 2: Context
    await emit_event("phase_started", {"phase": "context", "status": "running"})
    await context_phases(config)
    await emit_event("phase_completed", {"phase": "context", "scenes_processed": 50, "duration_s": 8.7})

# ✓ Good: CLI status command shows clear state
$ rentl show-status abc123
✓ Phase: translate (60% complete)
  - Lines processed: 750/1250
  - ETA: 2m 15s

# ✗ Bad: Ambiguous or delayed progress
async def run_pipeline(run_id: str) -> None:
    """Run pipeline with poor visibility."""
    # Silent ingestion, no updates
    await ingest_phases(config)
    # Silent context, no updates
    await context_phases(config)
    # Only shows progress at the very end
    await translate_phases(config)

# ✗ Bad: CLI status unclear
$ rentl show-status abc123
Running...
[No progress indicators, no phase information]
```

**Progress visibility requirements:**
- **Immediate:** Emit progress events at phase start, completion, and meaningful milestones
- **Unambiguous:** Clear phase name, status (running/completed/failed), and completion percentage
- **Granular enough:** Show line counts, token usage, or scene counts where applicable
- **ETA indicators:** Show estimated time remaining for long-running phases
- **Error visibility:** Failed lines or scenes are immediately visible, not buried at the end

**Progress by phase:**
- `phase_started` event with phase name and status
- Milestone updates within phase (e.g., every 100 lines translated)
- `phase_completed` event with completion metrics (lines processed, duration)
- `phase_failed` event with error context (what failed, why)

**Status indicators (CLI/TUI):**
- Phase name and status clearly visible
- Progress percentage or fraction (e.g., "750/1250 lines")
- Time elapsed and ETA
- Active animation or spinner for running phases
- Error messages inline with phase context

**Exceptions (brief initialization):**
Only during brief initialization (config loading, establishing connections) can have delayed/ambiguous progress. Emit initial status within 5 seconds or show "Initializing..." with clear startup phase name.

**Why:** Builds trust by showing what's done, what's next, and what failed; creates visible momentum and sense of progress; prevents "black box" anxiety where users don't know if things are working.

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

## testing/make-all-gate

# Make All Gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands
