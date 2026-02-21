spec_id: s0.1.45
issue: https://github.com/trevorWieland/rentl/issues/132
version: v0.1

# Spec: Test Infrastructure Overhaul

## Problem

The test suite has accumulated 36+ violations across 5 testing standards: mock boundaries are at the wrong level (internal functions instead of agent boundary), coverage enforcement only applies to unit tests, quality test timeouts exceed the 30s limit, tests exist outside the governed `tests/` tree, and integration/quality tests don't consistently use BDD style.

## Goals

- Fix all mock boundaries to use agent-level mocks and assert invocations
- Extend coverage enforcement to the integration tier
- Fix quality timeout to ≤30s
- Move all test files under the governed `tests/{unit,integration,quality}/` tree
- Adopt BDD style for integration and quality tests
- Discover and fix any additional violations beyond the 36 listed in the issue

## Non-Goals

- Adding new test cases for untested features (coverage of new code is out of scope)
- Coverage enforcement on the quality tier (quality tests validate LLM behavior, not code coverage)
- Changing test behavior or assertions beyond what's needed for standard compliance
- Refactoring production code (only test infrastructure changes)

## Acceptance Criteria

- [ ] All integration tests mock at agent boundary (`ProfileAgent.run`), not `_build_llm_runtime` or `pydantic_ai.Agent`
- [ ] All mocks are asserted for invocation
- [ ] Coverage threshold enforced on unit and integration tiers
- [ ] Quality test timeouts < 30s in both test code and Makefile
- [ ] All test files live under `tests/{unit,integration,quality}/` — no package-local tests
- [ ] Feature files integrated into tier structure (moved from `tests/features/`)
- [ ] Integration and quality tests use BDD Given/When/Then style
- [ ] All violations of the 5 standards are addressed (not just the 36 listed — full audit)
- [ ] `make all` passes
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No internal mocks in integration tests** — Integration tests must mock at `ProfileAgent.run()`, never at `_build_llm_runtime`, `pydantic_ai.Agent.run`, or other internals
2. **All mocks verified** — Every mock must assert it was actually invoked (no silent pass-throughs)
3. **No tests outside `tests/{unit,integration,quality}/`** — No package-local tests, no ad-hoc test locations
4. **Quality timeout ≤30s enforced in Makefile** — The `--timeout` flag for quality tests must be ≤30 (not 90)
5. **No test deletions to make gates pass** — Fix tests, don't remove them
