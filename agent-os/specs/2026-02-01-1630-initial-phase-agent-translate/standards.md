# Standards for Initial Phase Agent: Translate

The following standards apply to this work.

---

## testing/make-all-gate

`make all` must pass before merge. This mirrors CI and catches format/lint/type/test issues locally.

Rules:
- Run `make all` when a task or spec is complete and ready to finalize
- Fix failures and re-run until green
- Do not skip steps or substitute partial commands

---

## python/async-first-design

Design all APIs and I/O around `async`/`await` and modern structured concurrency.

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

---

## python/pydantic-only-schemas

Never use dataclasses or plain classes for schemas. All schemas must use Pydantic.

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

---

## testing/three-tier-test-structure

All tests in unit/integration/quality folders:
- unit <250ms
- integration <5s
- quality <30s

---

## testing/test-timing-rules

Strict timing limits per tier:
- unit <250ms
- integration <5s
- quality <30s

---

## architecture/adapter-interface-protocol

Never access infrastructure adapters directly; access protocols defined in the Core Domain.

The `TranslateDirectTranslatorAgent` implements `PhaseAgentProtocol[TranslatePhaseInput, TranslatePhaseOutput]`.

---

## ux/frictionless-by-default

Guided setup and safe defaults for effortless first runs.

Applied via:
- Default chunk_size of 50
- Default source_lang "ja" and target_lang "en"
- Automatic fallback text for missing context data
