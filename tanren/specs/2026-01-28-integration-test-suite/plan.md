# Integration Test Suite — Plan

**Roadmap Item:** (24) Integration Test Suite — Validate CLI workflows and runtime wiring across storage and BYOK endpoints.

**Depends on:** 11, 12, 13, 23

---

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-01-28-integration-test-suite/` with:

- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context)
- **standards.md** — Full content of the 6 applicable standards
- **references.md** — Pointer to `tests/integration/cli/test_validate_connection.py`

**Acceptance:** Spec folder exists with all 4 files.

---

## Task 2: Add pytest-bdd Dependency

Update `/home/trevor/github/rentl/pyproject.toml` to add `pytest-bdd>=8` to dev dependencies.

**Acceptance:** `uv sync` succeeds and `pytest-bdd` is importable.

---

## Task 3: Create BDD Infrastructure

Set up BDD scaffolding:

1. Create `tests/integration/features/` directory for `.feature` files
2. Create subdirectories: `features/cli/`, `features/storage/`, `features/byok/`
3. Update `tests/integration/conftest.py` with shared fixtures
4. Create step definition pattern (one module per component)

**Files to create:**
- `tests/integration/features/cli/` (directory)
- `tests/integration/features/storage/` (directory)
- `tests/integration/features/byok/` (directory)
- `tests/integration/steps/` (directory for step definitions)

**Acceptance:** Directory structure exists; conftest.py has shared fixtures.

---

## Task 4: Refactor validate-connection Test to BDD

Convert existing test to proper pytest-bdd format.

**Create:** `tests/integration/features/cli/validate_connection.feature`

**Refactor:** `tests/integration/cli/test_validate_connection.py` to use step definitions

**Acceptance:** `pytest tests/integration/cli/` passes with BDD-style tests.

---

## Task 5: CLI Command Integration Tests

Create BDD tests for all CLI commands:

- `version` command scenarios
- `export` command scenarios (success, error cases)
- `run-pipeline` command scenarios (with mocked LLM)
- `run-phase` command scenarios (with mocked LLM)

**Acceptance:** All CLI command scenarios pass; each test <5s.

---

## Task 6: Storage Adapter Integration Tests

Create BDD tests for storage operations:

- FileSystemRunStateStore round-trip scenarios
- FileSystemArtifactStore round-trip scenarios
- FileSystemLogStore round-trip scenarios
- Protocol compliance tests (prepare for PostgreSQL adapter abstraction)

**Acceptance:** Storage scenarios pass; protocol tests validate compliance.

---

## Task 7: BYOK Runtime Integration Tests

Create BDD tests for BYOK endpoints:

- OpenAICompatibleRuntime with mock HTTP endpoints
- Connection validation scenarios (success, failure, skipped)
- API key resolution scenarios

**Acceptance:** BYOK scenarios pass with mock HTTP server.

---

## Task 8: Update Makefile

Modify `/home/trevor/github/rentl/Makefile` to include integration tests in `make all`.

**Acceptance:** `make all` runs integration tests after unit tests.

---

## Task 9: Verification - Run make all

Run `make all` to ensure all code passes quality checks:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests with 80% coverage
- Run integration tests (<5s each)

**This task MUST pass before the spec is considered complete.**

**Acceptance:** `make all` exits with code 0; all checks pass.

---

## Summary

| Task | Description | Key Deliverables |
|------|-------------|------------------|
| 1 | Save Spec Documentation | 4 spec files in agent-os/specs/ |
| 2 | Add pytest-bdd | pyproject.toml updated |
| 3 | Create BDD Infrastructure | features/, steps/, conftest.py |
| 4 | Refactor validate-connection | BDD conversion complete |
| 5 | CLI Command Tests | 5 .feature files with scenarios |
| 6 | Storage Adapter Tests | filesystem.feature, protocol.feature |
| 7 | BYOK Runtime Tests | openai_runtime.feature |
| 8 | Update Makefile | integration in make all |
| 9 | Verification | make all passes |
