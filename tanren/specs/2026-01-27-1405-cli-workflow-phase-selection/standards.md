# Standards for CLI Workflow & Phase Selection

The following standards apply to this work.

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

**Why:** Enables swapping implementations (Chroma → pgvector, OpenAI → local models) without changing business logic, makes testing easier with mock protocols, and keeps the core domain clean of infrastructure concerns (Hexagonal/Clean Architecture).

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

## architecture/api-response-format

# API Response Format

All CLI JSON responses use `{data, error, meta}` envelope structure. Each field is a clearly defined Pydantic model.

```python
from pydantic import BaseModel, Field

# ✓ Good: Clear Pydantic models for envelope fields
class MetaInfo(BaseModel):
    """Metadata for API responses."""
    timestamp: str = Field(..., description="ISO-8601 timestamp")

class ErrorDetails(BaseModel):
    """Detailed error context."""
    field: str | None = Field(None, description="Field name if validation error")
    provided: str | None = Field(None, description="Value that was provided")
    valid_options: list[str] | None = Field(None, description="Valid values if applicable")

class ErrorResponse(BaseModel):
    """Error information in response."""
    code: str = Field(..., description="Error code (e.g., VAL_001)")
    message: str = Field(..., description="Human-readable error message")
    details: ErrorDetails | None = Field(None, description="Additional error context")

class APIResponse[T](BaseModel, Generic[T]):
    """Generic API response envelope."""
    data: T | None = Field(None, description="Success payload, null on error")
    error: ErrorResponse | None = Field(None, description="Error information, null on success")
    meta: MetaInfo = Field(..., description="Response metadata")
```

```json
// ✓ Good: Success response with Pydantic-validated types
{
  "data": {
    "run_id": "abc123",
    "status": "running",
    "phase": "translate"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-01-23T12:00:00Z"
  }
}

// ✓ Good: Error response with Pydantic-validated types
{
  "data": null,
  "error": {
    "code": "VAL_001",
    "message": "Invalid configuration: model not found",
    "details": {
      "field": "model",
      "provided": "gpt-5.2",
      "valid_options": ["gpt-4", "gpt-4.1", "gpt-4o"]
    }
  },
  "meta": {
    "timestamp": "2026-01-23T12:00:00Z"
  }
}

// ✗ Bad: Raw data without envelope
{
  "run_id": "abc123",
  "status": "running"
}

// ✗ Bad: Error without code or structure
{
  "error": "Something went wrong"
}
```

**Response envelope Pydantic model:**
- `data[T]`: Generic type containing success payload, null on error
- `error`: `ErrorResponse` model with `{code, message, details}`, null on success
- `meta`: `MetaInfo` or similar for audit metadata

**Error Pydantic model requirements:**
- `code`: Error identifier (e.g., `VAL_001`, `AUTH_001`, `DB_001`) as required string
- `message`: Human-readable error description as required string
- `details`: Optional `ErrorDetails` or similar for additional context

**Meta Pydantic model requirements:**
- Include timestamp for auditability
- Add version, request_id, or other metadata as needed

**Success response requirements:**
- Always include `data` field with typed payload
- `error` field must be `None` (never omitted in Pydantic model)
- Include `meta` with timestamp for auditability

**Error response requirements:**
- Always include both `code` and `message` in error model
- Include `details` when helpful (field names, valid options, suggestions)
- `data` field must be `None` (never omitted in Pydantic model)

**Exceptions (streaming/event-driven):**
Streaming responses and event-driven outputs (e.g., JSONL logs, SSE events) may use different structures as they don't fit single-response envelope.

**Why:** Frontend always knows where to find data or errors, consistent parsing without guessing schema per endpoint, predictable error handling, and type safety through Pydantic validation.

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

## architecture/none-vs-empty

# None vs Empty Lists

Use `None` to mean "not provided." Use `[]` to mean "provided but empty."

Rules:
- Optional list fields default to `None`
- If a phase runs and produces no items, return `[]`
- Do not omit required list fields; pass an empty list if there are no items

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

## ux/speed-with-guardrails

# Speed with Guardrails

Fast iterations without sacrificing determinism or quality signals. Speed and quality aren't tradeoffs.

```python
# ✓ Good: Fast iteration with quality guardrails
async def edit_cycle(run_id: str, review_notes: list[ReviewNote]) -> None:
    """Apply review notes with quality guardrails."""
    # Fast: Parallel processing
    tasks = [
        apply_fix(note) for note in review_notes
    ]
    results = await asyncio.gather(*tasks)
    
    # Guardrails: Quality checks before accepting
    if not await validate_qa_after_edit(results):
        # Don't break determinism - rollback and report
        await rollback_edits(results)
        raise QualityGuardrailError(
            "Edits failed QA guardrails. "
            "Style violations: 12, "
            "Consistency issues: 3. "
            "Review manually and retry."
        )
    
    # Success: Apply and continue momentum
    await apply_edits(results)
    await emit_event("edit_cycle_completed", {
        "edits_applied": len(results),
        "qa_passed": True,
        "duration_s": 2.3  # Fast iteration
    })

# ✓ Good: Hotfix loop with guardrails
async def hotfix_fix(issue: IssueReport) -> None:
    """Fix issue rapidly but maintain quality."""
    # Speed: Targeted fix
    fix = await generate_fix(issue)
    
    # Guardrails: Validate fix doesn't break similar lines
    similar_lines = await find_similar_lines(issue.context)
    for line in similar_lines:
        if not await validate_fix_preserves_context(line, fix):
            raise QualityGuardrailError(
                f"Fix breaks context for line {line.id}. "
                "Review fix and retry."
            )
    
    # Success: Apply fast but safe
    await apply_fix(issue, similar_lines)
    await emit_event("hotfix_applied", {
        "issue_id": issue.id,
        "lines_affected": len(similar_lines) + 1,
        "qa_passed": True
    })

# ✗ Bad: Speed without guardrails
async def edit_cycle(run_id: str, review_notes: list[ReviewNote]) -> None:
    """Apply review notes - fast but breaks quality."""
    # Fast: No validation
    for note in review_notes:
        fix = await generate_fix(note)
        await apply_fix(fix)  # Apply immediately, no QA check
    
    # No guardrails - breaks determinism and consistency
    # Style violations accumulate
    # Context breaks happen silently
    # Can't roll back if issues occur
```

**Speed principles:**
- **Parallel processing:** Run independent operations concurrently (e.g., multiple edit fixes at once)
- **Targeted operations:** Fix specific issues rather than re-running entire pipeline
- **Minimal rework:** Apply fixes directly, don't require full re-translation
- **Momentum preservation:** Each iteration should improve quality without requiring manual intervention

**Quality guardrails must enforce:**
- **Style consistency:** Fixes don't break established tone or style
- **Terminology:** Fixes maintain glossary and term consistency
- **Context preservation:** Fixes don't break scene context or character consistency
- **No regressions:** New fixes don't break existing correct translations

**Guardrail enforcement:**
- **Pre-apply validation:** Check quality before accepting changes
- **Rollback capability:** Revert changes if guardrails fail
- **Clear reporting:** Explain why guardrails rejected a change
- **Fast feedback:** Validation completes quickly (not blocking speed)

**Hotfix vs regular iterations:**
- **Hotfixes:** Targeted fixes with guardrails; can use `--fast` flag (future feature for emergency only)
- **Regular edits:** Full QA cycle with all guardrails; maintain quality at speed

**Never:**
- Bypass QA checks for speed (breaks determinism and trust)
- Apply edits that fail style or terminology guardrails
- Break context without validation
- Accumulate style violations in name of "speed"

**Why:** Enables rapid iteration cycles for quality improvement while maintaining reliability through quality checks; prevents breakage from rushed changes.

---

## testing/make-all-gate

# Make All Gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands
