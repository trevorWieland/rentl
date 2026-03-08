# Standards for Initial QA Checks (Deterministic)

The following standards apply to this work.

---

## testing/make-all-gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands

---

## testing/three-tier-test-structure

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

**Package structure mirrors source:**
- `tests/unit/core/` tests `rentl_core/`
- `tests/integration/cli/` tests `rentl_cli/`

---

## python/pydantic-only-schemas

Never use dataclasses or plain classes for schemas. All schemas must use Pydantic.

```python
# ✓ Good: Pydantic schema
from pydantic import BaseModel, Field

class TranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(..., pattern=r'^[a-z]{2}$', description="ISO 639-1 language code")
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
