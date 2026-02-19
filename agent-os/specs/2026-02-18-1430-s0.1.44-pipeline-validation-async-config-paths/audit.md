status: fail
fix_now_count: 2

# Audit: s0.1.44 Pipeline Validation, Async Correctness & Config Paths

- Spec: s0.1.44
- Issue: https://github.com/trevorWieland/rentl/issues/131
- Date: 2026-02-19
- Round: 1

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 4/5
- Completion: 4/5
- Security: 5/5
- Stability: 4/5

## Non-Negotiable Compliance
1. No unvalidated edit persistence: **PASS** — `_validate_edit_output(...)` runs before `_persist_phase_artifact(...)` in edit flow (`packages/rentl-core/src/rentl_core/orchestrator.py:1057`, `packages/rentl-core/src/rentl_core/orchestrator.py:1058`); validation enforces count/ID contract (`packages/rentl-core/src/rentl_core/orchestrator.py:2461`).
2. Schema validation, not syntax checks: **FAIL** — generated backup config assertions still use raw dict drilling instead of schema validation in integration tests (`tests/integration/cli/test_migrate.py:225`, `tests/integration/core/test_doctor.py:118`).
3. No blocking I/O in async functions: **PASS** — async paths use `asyncio.to_thread`/async filesystem APIs for file I/O (`services/rentl-cli/src/rentl/main.py:1225`, `services/rentl-cli/src/rentl/main.py:2915`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:56`, `packages/rentl-core/src/rentl_core/doctor.py:454`).
4. Path resolution from config parent, not CWD: **PASS** — doctor resolves via `config_path.parent` and workspace chain (`packages/rentl-core/src/rentl_core/doctor.py:266`, `packages/rentl-core/src/rentl_core/doctor.py:458`); agent validation script loads `.env` from config parent (`scripts/validate_agents.py:407`); agent path resolver enforces workspace containment (`packages/rentl-agents/src/rentl_agents/wiring.py:1234`).

## Demo Status
- Latest run: PASS (Run 1, 2026-02-18)
- `demo.md` reports all 6 required steps passing, including `make all` and targeted code-path verification.

## Standards Adherence
- `speed-with-guardrails` (`agent-os/standards/ux/speed-with-guardrails.md:84`): PASS — edit output is validated pre-persist (`packages/rentl-core/src/rentl_core/orchestrator.py:1057`).
- `validate-generated-artifacts` rule step 2 (`agent-os/standards/testing/validate-generated-artifacts.md:10`): **violation (High)** — raw dict assertions on generated backup configs (`tests/integration/cli/test_migrate.py:225`, `tests/integration/core/test_doctor.py:118`).
- `async-first-design` (`agent-os/standards/python/async-first-design.md:45`): PASS — no direct blocking file I/O observed in audited async paths.
- `config-path-resolution` (`agent-os/standards/architecture/config-path-resolution.md:7`): PASS — `.env` and workspace-relative resolution use config parent/workspace chain.
- `pydantic-only-schemas` (`agent-os/standards/python/pydantic-only-schemas.md:3`): PASS — audited schema validation paths use Pydantic models.
- `make-all-gate` (`agent-os/standards/testing/make-all-gate.md:3`): PASS (from demo evidence) — latest demo records `make all` as green.

## Regression Check
- `audit-log.md` shows all task-level audits and demo passing, but this spec-level sweep found remaining integration dict-drilling in backup assertions that should have been fully converted under Task 4.
- No signpost file was present in this spec folder (`signposts.md` missing), so no resolved/deferred signpost exemptions applied.

## Action Items

### Fix Now
- Replace raw backup version dict drilling with `RunConfig.model_validate` assertions in `tests/integration/cli/test_migrate.py:225` (tracked in `plan.md` Task 4, audit round 1).
- Replace raw backup version dict drilling with `RunConfig.model_validate` assertions in `tests/integration/core/test_doctor.py:118` (tracked in `plan.md` Task 4, audit round 1).

### Deferred
- None.
