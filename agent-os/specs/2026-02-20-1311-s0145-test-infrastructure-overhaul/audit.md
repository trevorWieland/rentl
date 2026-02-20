status: fail
fix_now_count: 3

# Audit: s0.1.45 Test Infrastructure Overhaul

- Spec: s0.1.45
- Issue: https://github.com/trevorWieland/rentl/issues/132
- Date: 2026-02-20
- Round: 2

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 3/5
- Completion: 3/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. No internal mocks in integration tests: **PASS** — forbidden internal targets are absent from integration tests (`rg -n "_build_llm_runtime|pydantic_ai.Agent.run" tests/integration` returned no matches).
2. All mocks verified: **FAIL** — integration mocks still exist without explicit invocation assertions: shared runtime monkeypatch has no call assertion (`tests/integration/conftest.py:156`), benchmark loader/judge mocks are not fully asserted (`tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/test_cli_command.py:646`, `tests/integration/benchmark/test_cli_command.py:728`), and one mocked HTTP route has no invocation assertion (`tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:280`).
3. No tests outside `tests/{unit,integration,quality}/`: **PASS** — no out-of-tier test files found (`git ls-files | rg '(^|/)test_.*\\.py$|(^|/).*_test\\.py$' | rg -v '^tests/(unit|integration|quality)/'` returned no matches; `find packages -type f -name 'test_*.py'` returned no matches).
4. Quality timeout ≤30s enforced in Makefile: **PASS** — quality target uses `--timeout=29` (`Makefile:79`).
5. No test deletions to make gates pass: **PASS** — no staged/working-tree deletions (`git status --short` contains no `D` entries) and migrated tests remain present (`tests/unit/core/test_explain.py`, `tests/unit/core/test_help.py`, `tests/unit/core/test_migrate.py`).

## Demo Status
- Latest run: PASS (Run 2, 2026-02-20)
- `agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/demo.md:34` through `agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/demo.md:42` shows all demo steps passing, including `make all`.

## Standards Adherence
- `mock-execution-boundary` (verify mocks invoked): **violation (High)** — missing explicit invocation verification for multiple integration mocks (`tests/integration/conftest.py:156`, `tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/test_cli_command.py:646`, `tests/integration/benchmark/test_cli_command.py:728`, `tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:280`).
- `mandatory-coverage`: **PASS** — unit and integration coverage gates are configured in `Makefile:69` and `Makefile:74`.
- `test-timing-rules`: **PASS** — quality timeout is below 30s in `Makefile:79`, and quality test markers are below 30s (`tests/quality/agents/test_pretranslation_agent.py:42`, `tests/quality/pipeline/test_golden_script_pipeline.py:38`).
- `three-tier-test-structure`: **PASS** — no package-local or ad-hoc test files detected; test files are in governed tiers.
- `bdd-for-integration-quality`: **PASS** — all integration and quality `test_*.py` files include `pytest_bdd` wiring and scenario linkage (tier-wide scan returned no missing files).
- `make-all-gate`: **PASS** — demo reports successful `make all` (`agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/demo.md:42`).
- `no-test-skipping`: **PASS** — no skip/xfail usage found (`rg -n "@pytest.mark.(skip|xfail)|pytest.skip\\(" tests` returned no matches).
- `no-mocks-for-quality-tests`: **PASS** — no quality-tier mock/patch usage found; only environment/path setup via `monkeypatch.chdir` (`tests/quality/cli/test_preset_validation.py:82`).

## Regression Check
- Previously fixed timeout and structure regressions remain fixed (`Makefile:79`, no out-of-tier test files).
- Previous audit round fixed several mock assertions, but full-suite audit still finds unverified mocks in less-traveled benchmark and shared-fixture paths, indicating incomplete closure of Task 3’s "assert every mock invocation" acceptance.

## Action Items

### Fix Now
- Add explicit invocation verification for the shared `mock_llm_runtime` monkeypatch (`OpenAICompatibleRuntime.run_prompt`) used by integration scenarios (`tests/integration/conftest.py:156`, `tests/integration/cli/test_doctor.py:33`, `tests/integration/cli/test_validate_connection.py:187`).
- Add explicit invocation assertions for remaining benchmark CLI mocks: `EvalSetLoader.get_slice_scripts` and `RubricJudge` in override scenarios (`tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/test_cli_command.py:646`, `tests/integration/benchmark/test_cli_command.py:728`).
- Add explicit invocation assertion for the mocked 404 download route (or remove unnecessary mocking) in the HTTP-error scenario (`tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:280`).

### Deferred
- None.
