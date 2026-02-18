spec_id: s0.1.44
issue: https://github.com/trevorWieland/rentl/issues/131
version: v0.1

# Spec: Pipeline Validation, Async Correctness & Config Paths

## Problem

The 2026-02-17 standards audit identified 17 violations across 4 standards: edit outputs are persisted without quality gates, test assertions use raw dict access instead of schema validation, sync file I/O blocks async functions, and path resolvers use incorrect bases. These gaps undermine pipeline reliability, test trustworthiness, and async performance.

## Goals

- Add quality gates between edit output merge and persistence
- Convert all test assertions for generated artifacts to use `model_validate`
- Wrap all sync file I/O in async contexts with `asyncio.to_thread`
- Fix path resolution to use correct bases (config parent / workspace_dir)

## Non-Goals

- Refactoring the overall orchestrator architecture
- Adding new test coverage beyond what's needed to verify the fixes
- Converting sync-only code paths to async (only fixing async paths that contain sync I/O)
- Changing the config schema itself

## Acceptance Criteria

- [ ] Quality gate validates edit outputs before persistence in orchestrator and agent wiring
- [ ] All test assertions for generated configs/artifacts use `model_validate` (covers violations #4-#9)
- [ ] All sync file I/O in async contexts wrapped in `asyncio.to_thread` (covers violations #10-#14)
- [ ] Doctor resolves workspace paths from `workspace_dir`, not `config_dir`
- [ ] `validate_agents.py` loads `.env` from config parent, not CWD
- [ ] Agent path resolver enforces workspace containment (no absolute path escapes)
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No unvalidated edit persistence** — Edit outputs must pass a quality gate before being written to disk; never persist then validate
2. **Schema validation, not syntax checks** — Every test assertion for generated config/artifacts must use the consuming component's `model_validate`, not raw dict/key checks
3. **No blocking I/O in async functions** — All file I/O within async contexts must use `asyncio.to_thread` or equivalent; sync calls in async paths are always a violation
4. **Path resolution from config parent, not CWD** — Doctor and agent path resolvers must derive bases from `config_path.parent` / `workspace_dir`, never from `os.getcwd()` or hardcoded assumptions
