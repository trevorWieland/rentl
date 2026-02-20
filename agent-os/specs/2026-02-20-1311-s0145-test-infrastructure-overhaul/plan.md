spec_id: s0.1.45
issue: https://github.com/trevorWieland/rentl/issues/132
version: v0.1

# Plan: Test Infrastructure Overhaul

## Decision Record

The test suite has accumulated violations across 5 testing standards due to organic growth. This spec addresses all violations systematically: restructure file locations first (least risk), then fix mock boundaries (highest impact), then coverage/timing enforcement, then BDD conversion, and finally a full sweep for any violations missed by the issue audit.

Coverage enforcement is scoped to unit and integration tiers only — quality tests validate LLM behavior and adding coverage thresholds there would pollute the tier with non-LLM tests.

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Restructure test file locations
  - Move `packages/rentl-core/tests/unit/core/test_explain.py`, `test_help.py`, `test_migrate.py` into `tests/unit/core/`
  - Move feature files from `tests/features/benchmark/` into corresponding tier directories
  - Remove empty `packages/rentl-core/tests/` and `tests/features/` directories
  - Update `pyproject.toml` test discovery config if paths are referenced
  - Acceptance: `find packages -name 'test_*' -type f` returns nothing; `tests/features/` doesn't exist
- [x] Task 3: Fix mock boundaries in integration tests
  - Refactor `tests/integration/cli/test_run_pipeline.py` — mock `ProfileAgent.run` instead of `_build_llm_runtime`
  - Refactor `tests/integration/cli/test_run_phase.py` — same fix
  - Refactor `tests/integration/benchmark/test_judge_flow.py` — mock at agent boundary instead of `pydantic_ai.Agent.run`
  - Refactor `tests/integration/byok/test_openrouter_runtime.py` — fix mock target and add invocation assertion
  - Fix `tests/integration/cli/test_onboarding_e2e.py` — add `ProfileAgent.run` invocation assertion
  - Scan all other integration tests for internal mock targets and fix
  - Add `assert call_count > 0` to every mock in integration tests
  - Acceptance: grep for `_build_llm_runtime` and `pydantic_ai.Agent.run` in integration tests returns zero; all mocks have assertions
  - [x] Fix: Make OpenRouter mocked responses schema-valid by including required OpenRouter fields (`choices[].native_finish_reason`, top-level `provider`) in `tests/integration/byok/test_openrouter_runtime.py:60` (audit round 1; `pytest -q tests/integration/byok/test_openrouter_runtime.py` fails with ValidationError).
  - [x] Fix: Add explicit invocation assertions (or remove unnecessary mocks) for `ProfileAgent.run` mocks in `tests/integration/cli/test_run_pipeline.py:157` and `tests/integration/cli/test_run_phase.py:151`; current `mock_call_count` values are never asserted (audit round 1; violates `mock-execution-boundary` and spec non-negotiable #2).
  - [x] Fix: Remove `_build_llm_runtime` literal references from integration-test comments/docstrings in `tests/integration/cli/test_run_pipeline.py:154`, `tests/integration/cli/test_run_phase.py:148`, and `tests/integration/conftest.py:151` so the Task 3 acceptance grep in `agent-os/specs/2026-02-20-1311-s0145-test-infrastructure-overhaul/plan.md:30` returns zero (audit round 1).
  - [x] Fix: Add explicit invocation assertion for the patched `_export_async` mock in `tests/integration/cli/test_exit_codes.py:275` (audit round 1; mock is patched but never explicitly asserted).
  - [x] Fix: Add explicit invocation assertions for patched `assert_preflight` mocks in `tests/integration/cli/test_init.py:264` and `tests/integration/cli/test_onboarding_e2e.py:162` (audit round 1; only `ProfileAgent.run` mock invocation is currently asserted).
  - [x] Fix: Add explicit invocation assertions for benchmark CLI mocks in `tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/test_cli_command.py:151`, and `tests/integration/benchmark/test_cli_command.py:429` (audit round 1; patched collaborators are not explicitly asserted as invoked).
  - [x] Fix: Add explicit `route.called` assertions for mocked HTTP routes in `tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:156` and `tests/integration/byok/test_local_model_factory.py:196` (audit round 1; mocked routes are configured without explicit invocation checks in these scenarios).
  - [x] Fix: Add explicit invocation verification for the shared `mock_llm_runtime` monkeypatch (`OpenAICompatibleRuntime.run_prompt`) used by integration scenarios so the patch cannot silently pass through (`tests/integration/conftest.py:156`, `tests/integration/cli/test_doctor.py:33`, `tests/integration/cli/test_validate_connection.py:187`) (audit round 2).
  - [x] Fix: Add explicit invocation assertions for remaining benchmark CLI mocks: `EvalSetLoader.get_slice_scripts` and `RubricJudge` in override-mode scenarios (`tests/integration/benchmark/test_cli_command.py:143`, `tests/integration/benchmark/test_cli_command.py:646`, `tests/integration/benchmark/test_cli_command.py:728`) (audit round 2).
  - [x] Fix: Add explicit invocation assertion for the mocked 404 download route (or remove the unnecessary mock) in the HTTP-error scenario (`tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:280`) (audit round 2).
  - [x] Fix: Add explicit invocation verification for the patched `EvalSetLoader.get_slice_scripts` mock (or remove the unnecessary patch) in benchmark download BDD flow; it is mocked but never asserted (`tests/integration/benchmark/test_cli_command.py:143`, no corresponding assertion in `tests/integration/benchmark/test_cli_command.py:185-207`) (audit round 3).
  - [x] Fix: Ensure every `mock_llm_runtime` integration fixture usage is explicitly verified (or removed if unnecessary): onboarding doctor flow currently injects the fixture without any `call_count` assertion (`tests/integration/cli/test_onboarding_e2e.py:122`), and init pipeline flow includes the fixture without asserting or using it (`tests/integration/cli/test_init.py:229`) (audit round 3).
  - [x] Fix: Remove or explicitly verify the unused `respx` mock created in the 404 Given-step (`tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:94`), which currently has no invocation assertion and violates the “all mocks verified” requirement (audit round 4).
- [x] Task 4: Enforce coverage on integration tier
  - Add `--cov=packages --cov=services --cov-fail-under=80` to integration Makefile target
  - Scope coverage modules correctly for integration tier
  - Fix `tests/unit/core/test_version.py` constant-only assertion (violation 9)
  - Verify `rentl_tui` has test presence or document gap
  - Acceptance: `make integration` enforces coverage threshold
- [x] Task 5: Fix test timing rules
  - Change Makefile quality timeout from `--timeout=90` to `--timeout=30`
  - Fix `tests/quality/pipeline/test_golden_script_pipeline.py` if timeout > 30s
  - Fix `tests/quality/agents/test_pretranslation_agent.py` if timeout ≥ 30s
  - Verify all quality tests complete within 30s
  - Acceptance: `make quality` passes with `--timeout=30`
  - [x] Fix: Reduce timeout marker below 30s in `tests/quality/agents/test_pretranslation_agent.py:42` (currently `pytest.mark.timeout(30)`, still `>= 30`; violates Task 5 sub-item and `test-timing-rules`) (audit round 1)
  - [x] Fix: Reduce timeout marker below 30s in `tests/quality/pipeline/test_golden_script_pipeline.py:38` (currently `pytest.mark.timeout(30)`; standard text says quality tests must be `< 30s`) (audit round 1)
- [x] Task 6: Convert integration tests to BDD style
  - Convert `tests/integration/core/test_deterministic_qa.py` to BDD Given/When/Then
  - Convert `tests/integration/core/test_doctor.py` to BDD
  - Convert `tests/integration/byok/test_openrouter_runtime.py` to BDD
  - Convert `tests/integration/storage/test_filesystem.py` to BDD
  - Convert `tests/integration/cli/test_init.py` to BDD
  - Scan all other integration tests for non-BDD style and convert
  - Create feature files in `tests/integration/` as needed
  - Acceptance: all integration tests use pytest_bdd Given/When/Then fixtures
- [x] Task 7: Convert quality tests to BDD style
  - Convert `tests/quality/cli/test_preset_validation.py` to BDD
  - Scan all other quality tests for non-BDD style and convert
  - Create feature files in `tests/quality/` as needed
  - Acceptance: all quality tests use pytest_bdd Given/When/Then fixtures
- [x] Task 8: Full audit sweep and cleanup
  - Scan entire test suite for any remaining violations of all 5 standards
  - Fix all violations found
  - Run `make all` and verify clean pass
  - Acceptance: `make all` passes; no remaining violations of any testing standard
  - [x] Fix: Move or rename ad-hoc `debug_test.py` so no test-named files exist outside `tests/{unit,integration,quality}/` (`debug_test.py:1`) (audit round 1).
