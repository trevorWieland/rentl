# Standards for Observability Surface (CLI Status Viewer)

The following standards apply to this work.

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

## testing/make-all-gate

# Make All Gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands
