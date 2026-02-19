spec_id: s0.1.44
issue: https://github.com/trevorWieland/rentl/issues/131
version: v0.1

# Plan: Pipeline Validation, Async Correctness & Config Paths

## Decision Record

The 2026-02-17 standards audit flagged 17 violations across 4 standards (speed-with-guardrails, validate-generated-artifacts, async-first-design, config-path-resolution). This spec addresses all 17 violations with surgical fixes grouped by concern area. No architectural refactoring — just targeted corrections to bring the codebase into compliance.

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Add edit output validation gates
  - Add quality gate in `orchestrator.py` between edit merge and persistence: reorder store-after-persist, add try/except rollback on failure (violation #1, #3)
  - Add post-edit aggregate validation in `wiring.py`: assert `len(edited_lines) == len(translated_lines)` and output line ID set matches input (violation #2)
  - Add unit tests for the new validation gates
  - Acceptance: edit outputs are never persisted without passing validation; aggregate mismatch raises
- [x] Task 3: Convert unit test assertions to schema validation
  - [x] Fix: Replace `ProjectConfig.model_validate` with `RunConfig.model_validate` in migration assertions at `tests/unit/cli/test_main.py:2702`, `tests/unit/cli/test_main.py:2714`, and `tests/unit/cli/test_main.py:2722`; if fixture completeness blocks this, update the test fixture to a full `RunConfig` payload first (audit round 1)
  - [x] Fix: Replace remaining raw dict drilling on generated `rentl.toml` assertions with `RunConfig.model_validate` + attribute access in `tests/unit/cli/test_main.py:2036`, `tests/unit/cli/test_main.py:2071`, and `tests/unit/cli/test_main.py:2142` (audit round 2)
  - `tests/unit/core/test_init.py:80` — Replace raw key-in-dict checks with `RunConfig.model_validate` (or delete redundant test since next test already validates) (violation #4)
  - `tests/unit/core/test_init.py:160` — Replace 5 raw key checks with `SourceLine.model_validate` (violation #5)
  - `tests/unit/cli/test_main.py:1998` — Add `RunConfig.model_validate`, switch to attribute access (violation #6)
  - `tests/unit/cli/test_main.py:2701` — Replace 3 blocks of migration dict drilling with `RunConfig.model_validate` + attribute access (violation #7)
  - `tests/unit/core/test_doctor.py:375` — Replace migration dict drilling with `RunConfig.model_validate` (violation #7 cont.)
  - Acceptance: no raw dict bracket access for generated config assertions in unit tests; all use `model_validate`
- [x] Task 4: Convert integration/quality test assertions to schema validation
  - `tests/integration/cli/test_migrate.py:160` — Replace 2 BDD step dict drilling with `RunConfig.model_validate` (violation #8)
  - `tests/integration/core/test_doctor.py:123` — Replace 2 blocks of dict drilling with `RunConfig.model_validate` (violation #8 cont.)
  - `tests/integration/cli/test_run_pipeline.py:25` — Add round-trip `RunConfig.model_validate` guard to `_write_pipeline_config` (violation #8)
  - `tests/integration/cli/test_run_phase.py:26` — Add round-trip `RunConfig.model_validate` guard to `_write_phase_config` (violation #8)
  - `tests/integration/cli/test_validate_connection.py:24` — Add round-trip `RunConfig.model_validate` guard (violation #8)
  - `tests/quality/pipeline/test_golden_script_pipeline.py:44` — Add round-trip `RunConfig.model_validate` guard (violation #8)
  - `tests/quality/cli/test_preset_validation.py:93` — Add `RunConfig.model_validate` between file-existence check and doctor invocation (violation #9)
  - [x] Fix: Replace backup schema-version dict drilling with `RunConfig.model_validate` + attribute assertions in `tests/integration/cli/test_migrate.py:225` (audit round 1)
  - [x] Fix: Replace backup schema-version dict drilling with `RunConfig.model_validate` + attribute assertions in `tests/integration/core/test_doctor.py:118` (audit round 1)
  - Acceptance: no config fixture writers without schema validation; no file-existence-only assertions for generated configs
- [ ] Task 5: Wrap sync I/O in async contexts
  - `services/rentl-cli/src/rentl/main.py:2811` — Wrap sync progress/report I/O in `asyncio.to_thread` (violation #10)
  - `services/rentl-cli/src/rentl/main.py:2609` — Wrap sync agent/prompt loaders in `asyncio.to_thread` (violation #11, critical)
  - `services/rentl-cli/src/rentl/main.py:1208` — Wrap sync manifest/slice loading in `asyncio.to_thread` (violation #12)
  - `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:35` — Wrap mkdir, sha256, write_bytes, unlink with `asyncio.to_thread` (violation #13)
  - `packages/rentl-core/src/rentl_core/doctor.py:423` — Wrap `_load_config_sync` call with `asyncio.to_thread` (violation #14)
  - Acceptance: no direct `open()`/`read()`/`write()`/`Path.mkdir()`/`Path.write_bytes()` calls inside async functions; all wrapped with `asyncio.to_thread`
  - [ ] Fix: `run_doctor()` directly calls sync `check_config_valid()` in async context even though `check_config_valid()` performs sync file I/O (`packages/rentl-core/src/rentl_core/doctor.py:448`, `packages/rentl-core/src/rentl_core/doctor.py:194`, `packages/rentl-core/src/rentl_core/doctor.py:225`, `packages/rentl-core/src/rentl_core/doctor.py:229`); run this validation path via `asyncio.to_thread` (audit round 2)
  - [ ] Fix: `_benchmark_compare_async()` calls sync config/.env loaders directly in async context (`services/rentl-cli/src/rentl/main.py:1447`, `services/rentl-cli/src/rentl/main.py:1494`, `services/rentl-cli/src/rentl/main.py:2205`, `services/rentl-cli/src/rentl/main.py:2227`); move these calls behind `asyncio.to_thread` or async equivalents (audit round 2)
  - [ ] Fix: `_run_pipeline_async()` and `_run_phase_async()` call `_build_export_targets()`, which runs sync `Path.mkdir()` in async paths (`services/rentl-cli/src/rentl/main.py:2902`, `services/rentl-cli/src/rentl/main.py:2956`, `services/rentl-cli/src/rentl/main.py:2861`); eliminate blocking mkdir in async paths (audit round 2)
- [x] Task 6: Fix config path resolution
  - `packages/rentl-core/src/rentl_core/doctor.py:264` — Resolve workspace paths from `workspace_dir` instead of `config_dir` (violation #15)
  - `scripts/validate_agents.py:406` — Load `.env` from config file parent, not CWD (violation #16)
  - `packages/rentl-agents/src/rentl_agents/wiring.py:1205` — Add workspace containment check to `_resolve_agent_path`; reject absolute paths that escape workspace (violation #17)
  - Add/update tests for path resolution correctness and containment enforcement
  - Acceptance: doctor uses `workspace_dir` as base; validate_agents resolves `.env` from config parent; agent path resolver raises on workspace escape
