status: fail
fix_now_count: 2

# Audit: s0.1.44 Pipeline Validation, Async Correctness & Config Paths

- Spec: s0.1.44
- Issue: https://github.com/trevorWieland/rentl/issues/131
- Date: 2026-02-19
- Round: 3

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 4/5
- Completion: 4/5
- Security: 5/5
- Stability: 4/5

## Non-Negotiable Compliance
1. No unvalidated edit persistence: **PASS** — orchestrator validates merged edit output before persistence (`packages/rentl-core/src/rentl_core/orchestrator.py:1057`, `packages/rentl-core/src/rentl_core/orchestrator.py:1058`), with explicit line-count and line-ID set checks in `_validate_edit_output` (`packages/rentl-core/src/rentl_core/orchestrator.py:2461`). Agent-side aggregate output validation is also enforced (`packages/rentl-agents/src/rentl_agents/wiring.py:973`).
2. Schema validation, not syntax checks: **PASS** — generated config/artifact assertions validate via schema models (`tests/unit/core/test_init.py:93`, `tests/unit/core/test_init.py:171`, `tests/unit/cli/test_main.py:2037`, `tests/integration/cli/test_migrate.py:206`, `tests/integration/cli/test_run_pipeline.py:124`, `tests/quality/cli/test_preset_validation.py:98`).
3. No blocking I/O in async functions: **FAIL** — async path still invokes sync file I/O in two places: `_benchmark_download_async()` calls `EvalSetLoader.get_slice_scripts()` (`services/rentl-cli/src/rentl/main.py:1237`), which synchronously reads slices via `load_slices()`/`Path.open()` (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/loader.py:110`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/loader.py:91`); `run_doctor()` calls `check_workspace_dirs()` directly (`packages/rentl-core/src/rentl_core/doctor.py:458`) and that check performs sync filesystem probes via `Path.exists()` (`packages/rentl-core/src/rentl_core/doctor.py:271`, `packages/rentl-core/src/rentl_core/doctor.py:273`, `packages/rentl-core/src/rentl_core/doctor.py:275`).
4. Path resolution from config parent, not CWD: **PASS** — doctor resolves workspace-relative paths from config parent (`packages/rentl-core/src/rentl_core/doctor.py:264`), `validate_agents.py` loads `.env` from config parent (`scripts/validate_agents.py:407`), and agent path resolution enforces workspace containment (`packages/rentl-agents/src/rentl_agents/wiring.py:1234`).

## Demo Status
- Latest run: PASS (Run 3, 2026-02-19)
- `demo.md` shows all six required steps passed, including `make all` and targeted checks for guardrails, schema validation, async wrappers, and path resolution (`agent-os/specs/2026-02-18-1430-s0.1.44-pipeline-validation-async-config-paths/demo.md:40`).
- No demo steps were marked skipped.

## Standards Adherence
- `speed-with-guardrails` (`agent-os/standards/ux/speed-with-guardrails.md:84`): PASS — pre-persist validation is implemented (`packages/rentl-core/src/rentl_core/orchestrator.py:1057`).
- `validate-generated-artifacts` step 2 (`agent-os/standards/testing/validate-generated-artifacts.md:10`): PASS — generated artifacts are validated via consuming schemas (`tests/integration/cli/test_run_phase.py:118`, `tests/quality/pipeline/test_golden_script_pipeline.py:169`).
- `async-first-design` (`agent-os/standards/python/async-first-design.md:37`, `agent-os/standards/python/async-first-design.md:45`): **violation (High)** — blocking file I/O remains on async execution paths (`services/rentl-cli/src/rentl/main.py:1237`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/loader.py:91`, `packages/rentl-core/src/rentl_core/doctor.py:458`).
- `config-path-resolution` (`agent-os/standards/architecture/config-path-resolution.md:7`, `agent-os/standards/architecture/config-path-resolution.md:10`): PASS — config-parent/workspace chain and containment behavior are implemented (`packages/rentl-core/src/rentl_core/doctor.py:266`, `packages/rentl-agents/src/rentl_agents/wiring.py:1234`).
- `pydantic-only-schemas` (`agent-os/standards/python/pydantic-only-schemas.md:3`): PASS — audited schema usage remains Pydantic-based (`tests/unit/core/test_init.py:93`, `tests/integration/core/test_doctor.py:118`).
- `make-all-gate` (`agent-os/standards/testing/make-all-gate.md:3`): PASS (demo evidence) — latest demo run records `make all` passing (`agent-os/specs/2026-02-18-1430-s0.1.44-pipeline-validation-async-config-paths/demo.md:41`).

## Regression Check
- Previously flagged async fixes in round 2 remain resolved: `run_doctor()` now wraps `check_config_valid()` in `asyncio.to_thread` (`packages/rentl-core/src/rentl_core/doctor.py:448`), `_benchmark_compare_async()` wraps config/.env loading in `asyncio.to_thread` (`services/rentl-cli/src/rentl/main.py:1493`, `services/rentl-cli/src/rentl/main.py:1494`), and `_run_pipeline_async()`/`_run_phase_async()` call `_build_export_targets()` via `asyncio.to_thread` (`services/rentl-cli/src/rentl/main.py:2902`, `services/rentl-cli/src/rentl/main.py:2956`).
- New round-3 finding: benchmark download slice resolution still has sync file I/O on an async path (`services/rentl-cli/src/rentl/main.py:1237` → `packages/rentl-core/src/rentl_core/benchmark/eval_sets/loader.py:91`), indicating Task 5 closure regressed from “all async paths” perspective.
- `signposts.md` is not present for this spec, so no resolved/deferred signpost exceptions apply.

## Action Items

### Fix Now
- `_benchmark_download_async()` must remove direct sync call path through `EvalSetLoader.get_slice_scripts()` and use `asyncio.to_thread` (or equivalent in-memory reuse) for slice-script resolution (`services/rentl-cli/src/rentl/main.py:1237`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/loader.py:97`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/loader.py:110`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/loader.py:91`).
- `run_doctor()` must execute `check_workspace_dirs()` behind `asyncio.to_thread` because it performs sync filesystem probes (`packages/rentl-core/src/rentl_core/doctor.py:458`, `packages/rentl-core/src/rentl_core/doctor.py:271`, `packages/rentl-core/src/rentl_core/doctor.py:273`, `packages/rentl-core/src/rentl_core/doctor.py:275`).

### Deferred
- None.
