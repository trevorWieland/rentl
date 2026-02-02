# Standards for Initial Phase Agent: QA

The following standards apply to this work.

---

## testing/make-all-gate

All code must pass `make all` before being considered complete:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests

This is enforced as the final verification task.

---

## testing/three-tier-test-structure

Tests are organized into three tiers:
- **Unit tests** (`tests/unit/`): < 250ms, mocks only, no external services
- **Integration tests** (`tests/integration/`): < 5s, minimal mocks, real services (NO real LLMs)
- **Quality tests** (`tests/quality/`): < 30s, minimal mocks, REAL LLMs

For this spec:
- Unit tests cover schema validation, utility functions
- Integration tests cover profile loading, agent creation, mocked LLM responses

---

## testing/bdd-for-integration-quality

Integration and quality tests use Given/When/Then BDD style:

```gherkin
Feature: Style Guide Critic Agent

  Scenario: Agent returns violations for style guide issues
    Given a style guide with honorific rules
    And a translation that anglicizes honorifics
    When the style guide critic reviews the translation
    Then it returns a violation with category "style"
```

---

## python/async-first-design

All agent execution uses `async`/`await`:
- `QaStyleGuideCriticAgent.run()` is async
- Enables parallel processing of chunks
- Consistent with other phase agents

---

## python/strict-typing-enforcement

No `Any` or `object` types. All types must be explicit:
- Pydantic Field descriptors for all schema fields
- Type hints on all function signatures
- ConfigDict(strict=True, extra="forbid") for schemas

---

## python/pydantic-only-schemas

All data crossing package boundaries uses Pydantic BaseModel:
- `StyleGuideViolation` — single violation
- `StyleGuideViolationList` — LLM output wrapper
- `QaIssue` — unified output format

---

## architecture/thin-adapter-pattern

The QA agent is a thin wrapper over ProfileAgent:
- `QaStyleGuideCriticAgent` handles chunking and merging
- `ProfileAgent` handles LLM interaction
- Business logic stays minimal in the wrapper
