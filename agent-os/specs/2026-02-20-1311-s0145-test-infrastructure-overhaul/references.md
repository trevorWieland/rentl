# References: Test Infrastructure Overhaul

## Issue

- https://github.com/trevorWieland/rentl/issues/132

## Standards

- `agent-os/standards/testing/mock-execution-boundary.md`
- `agent-os/standards/testing/mandatory-coverage.md`
- `agent-os/standards/testing/test-timing-rules.md`
- `agent-os/standards/testing/three-tier-test-structure.md`
- `agent-os/standards/testing/bdd-for-integration-quality.md`
- `agent-os/standards/testing/make-all-gate.md`
- `agent-os/standards/testing/no-test-skipping.md`
- `agent-os/standards/testing/no-mocks-for-quality-tests.md`

## Key Files (violations to fix)

- `Makefile` — coverage and timeout configuration
- `pyproject.toml` — test discovery config
- `tests/integration/cli/test_run_pipeline.py` — mock boundary
- `tests/integration/cli/test_run_phase.py` — mock boundary
- `tests/integration/benchmark/test_judge_flow.py` — mock boundary
- `tests/integration/byok/test_openrouter_runtime.py` — mock boundary + BDD
- `tests/integration/cli/test_onboarding_e2e.py` — mock assertion
- `tests/integration/core/test_deterministic_qa.py` — BDD conversion
- `tests/integration/core/test_doctor.py` — BDD conversion
- `tests/integration/storage/test_filesystem.py` — BDD conversion
- `tests/integration/cli/test_init.py` — BDD conversion
- `tests/quality/pipeline/test_golden_script_pipeline.py` — timeout
- `tests/quality/agents/test_pretranslation_agent.py` — timeout
- `tests/quality/cli/test_preset_validation.py` — BDD conversion
- `tests/unit/core/test_version.py` — constant-only assertion
- `packages/rentl-core/tests/` — tests to relocate
- `tests/features/` — feature files to relocate

## Audit Reports

- `agent-os/audits/2026-02-17/`
