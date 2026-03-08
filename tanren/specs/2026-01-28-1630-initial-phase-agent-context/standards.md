# Standards for Initial Phase Agent: Context

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
├── integration/    # <5s per test, minimal mocks, real services, NO LLMs
└── quality/        # <30s per test, minimal mocks, real services, REAL LLMs
```

**Tier definitions:**

- **Unit tests**: Fast (<250ms), mocks allowed, no external services
- **Integration tests**: Moderate (<5s), minimal mocks, real services, NO LLMs
- **Quality tests**: Slower (<30s), real services, REAL LLMs

---

## testing/test-timing-rules

Performance budgets per test tier:

| Tier | Max Time | Notes |
|------|----------|-------|
| Unit | <250ms | Mocked, isolated |
| Integration | <5s | Real services except LLMs |
| Quality | <30s | Real LLMs allowed |

---

## python/async-first-design

Design all APIs and I/O around `async`/`await` and modern structured concurrency.

**Why async-first matters:**
- Parallel execution: Many phases run agents in parallel
- Network IO efficiency: LLM calls are network-bound
- Scalability: Avoid blocking on slow external services

**Requirements:**
- All I/O operations use async/await
- Use asyncio.gather, asyncio.TaskGroup for concurrency
- Avoid blocking operations in async paths

---

## python/strict-typing-enforcement

No `Any`, strict Pydantic schemas.

**Rules:**
- Never use `Any` or `object` in type hints
- All Pydantic fields use `Field` with description
- Enable strict mode on Pydantic models
- Catch type errors at initialization, not runtime

---

## python/pydantic-only-schemas

Pydantic for all data boundaries (no dataclasses).

**Rules:**
- All schemas inherit from BaseSchema
- Use Field() for all fields with description
- Validators for complex constraints
- No dataclasses in public APIs

---

## architecture/adapter-interface-protocol

Logic depends on Protocols (Ports), not implementations (Adapters).

**For this spec:**
- ProfileAgent implements PhaseAgentProtocol
- ToolRegistry uses AgentToolProtocol
- Loader uses protocols for storage access

---

## ux/frictionless-by-default

Guided setup and safe defaults.

**For this spec:**
- Default prompts work out of the box
- No configuration required for basic use
- Model recommendations suggest good starting points
- Clear error messages guide users to solutions
