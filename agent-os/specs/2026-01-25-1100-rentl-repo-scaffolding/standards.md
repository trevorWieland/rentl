# Standards for rentl Repository Scaffolding

The following standards apply to this work.

---

## global/thin-adapter-pattern

# Thin Adapter Pattern

CLI, TUI, and API layers are **thin adapters only**. All business logic lives in `rentl-core`.

```python
# ✓ Good: CLI is a thin wrapper
def run_pipeline(run_id: str):
    """Start pipeline run - thin adapter over core API."""
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

**Core logic includes:**
- Pipeline orchestration and phase execution
- Data transformation and validation
- Agent orchestration
- Storage operations
- Model integration

**Surface layers may contain:**
- Command definitions and argument parsing
- Output formatting (pretty-print, JSON wrapper)
- Truly surface-specific features that will never be reused

**Even validation and formatting should use contract models from `rentl-core`** - never duplicate schemas or business rules.

**Why:** Ensures core logic is reusable across CLI/TUI/API without duplication and makes testing easier (test core once, surfaces are thin wrappers).

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
