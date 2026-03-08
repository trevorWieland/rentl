# Standards for Run Persistence & Artifact Store Protocols

The following standards apply to this work.

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

## testing/make-all-gate

# Make All Gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands
