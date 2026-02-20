status: fail
fix_now_count: 5

# Audit: s0.1.45 Test Infrastructure Overhaul

- Spec: s0.1.45
- Issue: https://github.com/trevorWieland/rentl/issues/132
- Date: 2026-02-20
- Round: 1

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 3/5
- Completion: 2/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. No internal mocks in integration tests: **PASS** — forbidden internal targets are absent from integration tests (`tests/integration/cli/test_run_pipeline.py:154`, `tests/integration/cli/test_run_phase.py:148`; repo scan for `_build_llm_runtime|pydantic_ai.Agent.run` returned zero matches).
2. All mocks verified: **FAIL** — multiple integration mocks are patched without explicit invocation assertions (`tests/integration/cli/test_exit_codes.py:275`, `tests/integration/cli/test_init.py:264`, `tests/integration/cli/test_onboarding_e2e.py:162`, `tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:156`).
3. No tests outside `tests/{unit,integration,quality}/`: **FAIL** — ad-hoc test-named file exists outside governed tree (`debug_test.py:1`).
4. Quality timeout ≤30s enforced in Makefile: **PASS** — quality target uses `--timeout=29` (`Makefile:79`).
5. No test deletions to make gates pass: **PASS** — relocated tests required by Task 2 are present in governed tree (`tests/unit/core/test_explain.py`, `tests/unit/core/test_help.py`, `tests/unit/core/test_migrate.py`) and current worktree shows no deleted files (`git status --short` has no `D` entries).

## Demo Status
- Latest run: PASS (Run 1, 2026-02-20)
- Demo evidence in `agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/demo.md:24` through `agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/demo.md:32` shows all 7 run steps passing, including `make all`.

## Standards Adherence
- `mock-execution-boundary` (rule: verify mocks invoked): **violation (High)** — patched mocks without explicit invocation assertions in `tests/integration/cli/test_exit_codes.py:275`, `tests/integration/cli/test_init.py:264`, `tests/integration/cli/test_onboarding_e2e.py:162`, `tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:156`.
- `mandatory-coverage`: **PASS** — unit and integration coverage thresholds enforced in `Makefile:69` and `Makefile:74`.
- `test-timing-rules`: **PASS** — quality timeout enforcement is below 30s in `Makefile:79`, `tests/quality/agents/test_pretranslation_agent.py:42`, and `tests/quality/pipeline/test_golden_script_pipeline.py:38`.
- `three-tier-test-structure`: **violation (High)** — test-named file outside governed tiers (`debug_test.py:1`).
- `bdd-for-integration-quality`: **PASS** — all integration and quality `test_*.py` files include pytest-bdd scenario wiring and Given/When/Then steps (scan complete with zero missing files).
- `make-all-gate`: **PASS** — latest demo run reports `make all` passing (`agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/demo.md:31`).
- `no-test-skipping`: **PASS** — no skip/xfail patterns found in `tests/` (scan complete with zero matches).
- `no-mocks-for-quality-tests`: **PASS** — no mock/patch usage found in quality tests beyond non-mocking environment setup (`tests/quality/cli/test_preset_validation.py:82` uses `monkeypatch.chdir` only).

## Regression Check
- Task 3 and Task 5 previously marked fixed in `agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/audit-log.md:10` and `agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/audit-log.md:13`; timeout-related fixes remain intact (`Makefile:79`, `tests/quality/agents/test_pretranslation_agent.py:42`, `tests/quality/pipeline/test_golden_script_pipeline.py:38`).
- Mock-verification coverage regressed at full-suite level: prior task-level checks caught targeted files, but additional unasserted mocks remain in other integration suites (see Standards violations above).

## Action Items

### Fix Now
- Add explicit invocation assertion for patched `_export_async` mock (`tests/integration/cli/test_exit_codes.py:275`).
- Add explicit invocation assertions for patched `assert_preflight` mocks (`tests/integration/cli/test_init.py:264`, `tests/integration/cli/test_onboarding_e2e.py:162`).
- Add explicit invocation assertions for benchmark CLI mocks (`tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/test_cli_command.py:151`, `tests/integration/benchmark/test_cli_command.py:429`).
- Add explicit `route.called` assertions for mocked HTTP routes (`tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:156`, `tests/integration/byok/test_local_model_factory.py:196`).
- Move or rename ad-hoc `debug_test.py` so no test-named files exist outside tiered test directories (`debug_test.py:1`).

### Deferred
- None.
