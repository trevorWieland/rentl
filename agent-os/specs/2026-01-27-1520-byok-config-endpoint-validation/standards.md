# Standards for BYOK Config & Endpoint Validation

The following standards apply to this work.

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
