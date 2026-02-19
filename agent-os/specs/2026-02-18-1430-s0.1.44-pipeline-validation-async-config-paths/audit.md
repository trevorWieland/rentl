status: fail
fix_now_count: 3

# Audit: s0.1.44 Pipeline Validation, Async Correctness & Config Paths

- Spec: s0.1.44
- Issue: https://github.com/trevorWieland/rentl/issues/131
- Date: 2026-02-19
- Round: 2

## Rubric Scores (1-5)
- Performance: 3/5
- Intent: 4/5
- Completion: 3/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. No unvalidated edit persistence: **PASS** — edit outputs are validated before persistence in orchestrator (`packages/rentl-core/src/rentl_core/orchestrator.py:1057`, `packages/rentl-core/src/rentl_core/orchestrator.py:1058`) with explicit line-count/ID guardrails (`packages/rentl-core/src/rentl_core/orchestrator.py:2461`).
2. Schema validation, not syntax checks: **PASS** — generated config/artifact assertions use consuming schema validation (`tests/unit/core/test_init.py:93`, `tests/integration/cli/test_migrate.py:224`, `tests/integration/core/test_doctor.py:118`, `tests/integration/cli/test_run_pipeline.py:124`, `tests/quality/cli/test_preset_validation.py:98`).
3. No blocking I/O in async functions: **FAIL** — async paths still execute sync filesystem operations: `run_doctor()` calls sync `check_config_valid()` (`packages/rentl-core/src/rentl_core/doctor.py:448`) which performs sync file reads/writes (`packages/rentl-core/src/rentl_core/doctor.py:194`, `packages/rentl-core/src/rentl_core/doctor.py:225`, `packages/rentl-core/src/rentl_core/doctor.py:229`); `_benchmark_compare_async()` calls sync config/.env loaders (`services/rentl-cli/src/rentl/main.py:1447`, `services/rentl-cli/src/rentl/main.py:1494`, `services/rentl-cli/src/rentl/main.py:2205`); async run paths call `_build_export_targets()` which performs sync `Path.mkdir()` (`services/rentl-cli/src/rentl/main.py:2902`, `services/rentl-cli/src/rentl/main.py:2956`, `services/rentl-cli/src/rentl/main.py:2861`).
4. Path resolution from config parent, not CWD: **PASS** — doctor workspace resolution is chained from config parent to workspace (`packages/rentl-core/src/rentl_core/doctor.py:266`), agent validation script loads `.env` from config parent (`scripts/validate_agents.py:407`), and agent path resolution enforces workspace containment (`packages/rentl-agents/src/rentl_agents/wiring.py:1234`).

## Demo Status
- Latest run: PASS (Run 2, 2026-02-18)
- `demo.md` reports all six required run steps passing, including `make all` and targeted validation of edit guardrails, schema assertions, async I/O fixes, and path containment.

## Standards Adherence
- `speed-with-guardrails` (`agent-os/standards/ux/speed-with-guardrails.md:84`): PASS — pre-persist edit validation is in place (`packages/rentl-core/src/rentl_core/orchestrator.py:1057`).
- `validate-generated-artifacts` rule step 2 (`agent-os/standards/testing/validate-generated-artifacts.md:10`): PASS — generated config/artifact tests validate against `RunConfig`/`SourceLine` schemas (`tests/unit/core/test_init.py:93`, `tests/integration/cli/test_migrate.py:224`, `tests/quality/pipeline/test_golden_script_pipeline.py:169`).
- `async-first-design` (`agent-os/standards/python/async-first-design.md:37`, `agent-os/standards/python/async-first-design.md:45`): **violation (High)** — blocking filesystem operations remain on async execution paths (`packages/rentl-core/src/rentl_core/doctor.py:448`, `services/rentl-cli/src/rentl/main.py:1494`, `services/rentl-cli/src/rentl/main.py:2861`).
- `config-path-resolution` (`agent-os/standards/architecture/config-path-resolution.md:7`, `agent-os/standards/architecture/config-path-resolution.md:10`): PASS — config-parent/workspace chain and containment are enforced (`scripts/validate_agents.py:407`, `packages/rentl-agents/src/rentl_agents/wiring.py:1234`).
- `pydantic-only-schemas` (`agent-os/standards/python/pydantic-only-schemas.md:3`): PASS — audited schema contracts remain Pydantic-based in code and tests (`tests/integration/core/test_doctor.py:118`, `tests/unit/core/test_init.py:171`).
- `make-all-gate` (`agent-os/standards/testing/make-all-gate.md:3`): PASS (demo evidence) — latest demo run records `make all` green in Run 2 (`agent-os/specs/2026-02-18-1430-s0.1.44-pipeline-validation-async-config-paths/demo.md:32`).

## Regression Check
- Prior round-1 schema-validation failures in backup assertions are resolved (`tests/integration/cli/test_migrate.py:224`, `tests/integration/core/test_doctor.py:118`) and no duplicate fix item is open for that issue.
- `audit-log.md` shows Task 5 previously marked PASS, but this round found residual blocking I/O in additional async paths (doctor and benchmark/run helpers), indicating incomplete closure of the async-first standard.
- `signposts.md` is absent for this spec, so no resolved/deferred signpost exception applies.

## Action Items

### Fix Now
- Wrap `check_config_valid(config_path)` behind `asyncio.to_thread` (or equivalent async boundary) when called from `run_doctor()` to remove sync config file I/O from async path (`packages/rentl-core/src/rentl_core/doctor.py:448`, `packages/rentl-core/src/rentl_core/doctor.py:194`, `packages/rentl-core/src/rentl_core/doctor.py:225`, `packages/rentl-core/src/rentl_core/doctor.py:229`).
- Move `_benchmark_compare_async()` config/.env load path to async-safe execution (`asyncio.to_thread` or async API) so sync file reads no longer run on the event loop (`services/rentl-cli/src/rentl/main.py:1447`, `services/rentl-cli/src/rentl/main.py:1494`, `services/rentl-cli/src/rentl/main.py:2205`).
- Remove sync `Path.mkdir()` from async run paths by moving export-target directory creation behind async-safe execution (`services/rentl-cli/src/rentl/main.py:2861`, `services/rentl-cli/src/rentl/main.py:2902`, `services/rentl-cli/src/rentl/main.py:2956`).

### Deferred
- None.
