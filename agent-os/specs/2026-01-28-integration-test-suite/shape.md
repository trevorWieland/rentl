# Integration Test Suite — Shaping Notes

## Scope

Validate CLI workflows and runtime wiring across storage and BYOK endpoints. This is roadmap item (24), blocking v0.1 completion.

**What we're building:**
- Full pytest-bdd integration test suite with Gherkin .feature files
- Coverage for all 5 CLI commands: version, validate-connection, export, run-pipeline, run-phase
- Storage adapter integration tests (FileSystem* implementations + protocol compliance)
- BYOK runtime integration tests (OpenAICompatibleRuntime with mock HTTP)
- Integration tests added to `make all` as a mandatory gate

**Success criteria:**
- All integration tests green
- Full type checked to strict repo standards
- Uses BDD (pytest-bdd with .feature files)
- Added as mandatory part of `make all`

## Decisions

- **BDD Framework:** Full pytest-bdd with Gherkin .feature files (not docstring-style)
- **Command Priority:** All 5 CLI commands covered
- **Storage Scope:** FileSystem adapters + protocol abstractions for future PostgreSQL adapters
- **LLM Mocking:** Integration tests mock LLMs; quality tests (separate tier) use real LLMs

## Context

- **Visuals:** None needed
- **References:** `tests/integration/cli/test_validate_connection.py` (existing integration test pattern)
- **Product alignment:** Roadmap item (24) in v0.1: Playable Patch milestone

## Standards Applied

- **testing/bdd-for-integration-quality** — Integration tests must use BDD-style with pytest-bdd
- **testing/three-tier-test-structure** — Tests in unit/integration/quality folders; integration <5s
- **testing/make-all-gate** — `make all` must pass before finalization
- **testing/mandatory-coverage** — All features must have coverage exercising real behavior
- **testing/no-mocks-for-quality-tests** — Integration tests mock LLMs, quality tests use real LLMs
- **architecture/thin-adapter-pattern** — CLI is thin adapter; test core logic via CLI surface
