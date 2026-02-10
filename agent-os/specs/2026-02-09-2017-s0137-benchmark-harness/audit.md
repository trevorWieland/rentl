status: fail
fix_now_count: 1

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 7

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 5/5
- Completion: 4/5
- Security: 5/5
- Stability: 5/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — benchmark source text is fetched at runtime from KSRE (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:79`) with hash validation (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:87`), while repo artifacts are manifest/slice metadata only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`).
2. **Apples-to-apples comparison**: **PASS** — compare enforces shared line-ID coverage before judging (`services/rentl-cli/src/rentl_cli/main.py:1313`, `packages/rentl-core/src/rentl_core/benchmark/output_loader.py:67`) and uses a single judge model/runtime configuration for all pairwise calls (`services/rentl-cli/src/rentl_cli/main.py:1329`, `services/rentl-cli/src/rentl_cli/main.py:1396`).
3. **Scores must include per-line evidence**: **PASS** — per-line reasoning is a required schema field (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`), judge output parsing rejects missing reasoning (`packages/rentl-core/src/rentl_core/benchmark/judge.py:129`), and report schema stores per-line head-to-head results (`packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:51`).
4. **Benchmark must be runnable standalone**: **PASS** — first-class CLI commands exist for `benchmark download` and `benchmark compare` (`services/rentl-cli/src/rentl_cli/main.py:1099`, `services/rentl-cli/src/rentl_cli/main.py:1228`) and bridge immediately to async implementations (`services/rentl-cli/src/rentl_cli/main.py:1116`, `services/rentl-cli/src/rentl_cli/main.py:1262`).

## Demo Status
- Latest run: **PASS** (Run 8, 2026-02-10; `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:80`).
- Summary: Step 1 executes successfully; Steps 2-5 are explicitly skipped for external API/runtime constraints with quality-test substitution justification (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:81`).
- Verification gate: **PASS** — `make all` rerun during this audit (format, lint, type, unit, integration, quality all green).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark tests are present in unit/integration/quality tiers (`tests/unit/benchmark/test_output_loader.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`; standard `agent-os/standards/testing/three-tier-test-structure.md:3`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality benchmark test runs real CLI compare using configured endpoint/API key and does not mock judge/runtime (`tests/quality/benchmark/test_benchmark_quality.py:134`, `tests/quality/benchmark/test_benchmark_quality.py:159`; standard `agent-os/standards/testing/no-mocks-for-quality-tests.md:41`).
- `testing/bdd-for-integration-quality`: **violation (Medium)** — `tests/integration/benchmark/eval_sets/test_download_flow.py` uses direct pytest async tests/class structure rather than Given/When/Then BDD scenario bindings (`tests/integration/benchmark/eval_sets/test_download_flow.py:17`), which conflicts with integration-tier BDD requirement (`agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark contracts are Pydantic models (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`; standard `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — benchmark I/O paths are async and compare uses structured concurrency (`services/rentl-cli/src/rentl_cli/main.py:1273`, `services/rentl-cli/src/rentl_cli/main.py:1425`; standard `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — benchmark schema fields are explicitly typed with `Field(..., description=...)` (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:42`; standard `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **PASS** — download/compare show explicit progress and contextual error messaging (`services/rentl-cli/src/rentl_cli/main.py:1151`, `services/rentl-cli/src/rentl_cli/main.py:1409`, `services/rentl-cli/src/rentl_cli/main.py:1316`; standard `agent-os/standards/ux/trust-through-transparency.md:67`).
- `testing/validate-generated-artifacts`: **PASS** — generated benchmark report artifacts are validated through the consuming schema in integration/quality tests (`tests/integration/benchmark/test_cli_command.py:427`, `tests/quality/benchmark/test_benchmark_quality.py:169`; standard `agent-os/standards/testing/validate-generated-artifacts.md:10`).

## Regression Check
- Previously recurring failures from rounds 2-6 are no longer present in current code/tests: compare progress monotonicity, dead monolithic benchmark path, quality winner-label assertions, and full mocked compare flow coverage (historical failures logged at `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:50`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:54`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:56`).
- Remaining cross-cutting gap is standards conformance for integration-tier BDD coverage in eval-set download flow (`tests/integration/benchmark/eval_sets/test_download_flow.py:17`).

## Action Items

### Fix Now
- Convert benchmark eval-set download integration coverage to BDD Given/When/Then scenarios (feature-backed) instead of direct pytest integration tests (`tests/integration/benchmark/eval_sets/test_download_flow.py:17`, `agent-os/standards/testing/bdd-for-integration-quality.md:3`).

### Deferred
- None.
