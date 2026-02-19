# References: Pipeline Validation, Async Correctness & Config Paths

## Issue

- https://github.com/trevorWieland/rentl/issues/131

## Source: Standards Audit

- Audit reports: `agent-os/audits/2026-02-17/`

## Implementation Files (violations)

### speed-with-guardrails (violations #1-3)
- `packages/rentl-core/src/rentl_core/orchestrator.py:1002` — edit output persistence flow
- `packages/rentl-core/src/rentl_core/orchestrator.py:2990` — export line selection
- `packages/rentl-agents/src/rentl_agents/wiring.py:900` — post-edit validation gap

### validate-generated-artifacts (violations #4-9)
- `tests/unit/core/test_init.py:80` — raw key checks for config
- `tests/unit/core/test_init.py:160` — raw key checks for seed artifacts
- `tests/unit/cli/test_main.py:1998` — CLI init raw dict access
- `tests/unit/cli/test_main.py:2701` — migration dict drilling
- `tests/unit/core/test_doctor.py:375` — migration dict drilling
- `tests/integration/cli/test_migrate.py:160` — migration BDD steps
- `tests/integration/core/test_doctor.py:123` — migration dict drilling
- `tests/integration/cli/test_run_pipeline.py:25` — config fixture writer
- `tests/integration/cli/test_run_phase.py:26` — config fixture writer
- `tests/integration/cli/test_validate_connection.py:24` — config fixture writer
- `tests/quality/pipeline/test_golden_script_pipeline.py:44` — config fixture writer
- `tests/quality/cli/test_preset_validation.py:93` — file existence only

### async-first-design (violations #10-14)
- `services/rentl-cli/src/rentl/main.py:2811` — sync progress/report I/O
- `services/rentl-cli/src/rentl/main.py:2609` — sync agent/prompt loaders (critical)
- `services/rentl-cli/src/rentl/main.py:1208` — sync benchmark manifest loading
- `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:35` — blocking file ops
- `packages/rentl-core/src/rentl_core/doctor.py:423` — sync TOML I/O

### config-path-resolution (violations #15-17)
- `packages/rentl-core/src/rentl_core/doctor.py:264` — workspace path base
- `scripts/validate_agents.py:406` — .env loading from CWD
- `packages/rentl-agents/src/rentl_agents/wiring.py:1205` — agent path containment

## Related Specs

- s0.1.07, s0.1.08, s0.1.12, s0.1.13 (dependencies — all completed)
