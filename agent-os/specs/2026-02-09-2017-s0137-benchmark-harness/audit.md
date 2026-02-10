status: fail
fix_now_count: 4

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 5

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 4/5
- Completion: 2/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — eval text is fetched at runtime from KSRE raw GitHub (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:79`) with hash checks (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:86`), while committed eval assets are metadata only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`).
2. **Apples-to-apples comparison**: **PASS** — compare enforces matching line IDs before judging (`services/rentl-cli/src/rentl_cli/main.py:1313`, `packages/rentl-core/src/rentl_core/benchmark/output_loader.py:67`) and uses one shared runtime/model configuration for all pairwise calls (`services/rentl-cli/src/rentl_cli/main.py:1329`, `services/rentl-cli/src/rentl_cli/main.py:1396`).
3. **Scores must include per-line evidence**: **PASS** — reasoning is required in the schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`), parsing enforces reasoning presence (`packages/rentl-core/src/rentl_core/benchmark/judge.py:129`), and per-line results are persisted in report output (`packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:51`).
4. **Benchmark must be runnable standalone**: **PASS** — first-class CLI commands exist (`services/rentl-cli/src/rentl_cli/main.py:1099`, `services/rentl-cli/src/rentl_cli/main.py:1228`) and `uv run rentl benchmark --help` lists `download` and `compare`.

## Demo Status
- Latest run: **PASS** (Run 6, 2026-02-10; `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:64`)
- Results are acceptable for environment constraints: Step 1 executed; Steps 2-5 are skipped with explicit external-service/runtime rationale and quality-test substitution (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:65`).
- Verification gate rerun during this audit: `make all` passed (format/lint/type/unit/integration/quality).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark coverage exists in unit/integration/quality tiers (`tests/unit/benchmark/test_output_loader.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`; standard `agent-os/standards/testing/three-tier-test-structure.md:3`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality benchmark flow invokes real CLI compare with real endpoint configuration (`tests/quality/benchmark/test_benchmark_quality.py:134`; standard `agent-os/standards/testing/no-mocks-for-quality-tests.md:41`).
- `testing/bdd-for-integration-quality`: **PASS** — integration and quality suites use Given/When/Then BDD structure (`tests/integration/benchmark/test_cli_command.py:32`, `tests/quality/benchmark/test_benchmark_quality.py:66`; standard `agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark schema contracts are Pydantic models (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`; standard `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — compare execution uses async APIs and structured concurrency (`services/rentl-cli/src/rentl_cli/main.py:1273`, `services/rentl-cli/src/rentl_cli/main.py:1420`; standard `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — schema fields are strictly typed and documented with `Field(description=...)` (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:42`; standard `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **violation (Medium)** — progress completion uses task index (`services/rentl-cli/src/rentl_cli/main.py:1417`) and can regress under out-of-order completion; reproduced with staggered completion as `updates [2, 3, 1]`, final `1` for `3` tasks; this violates transparent progress expectations (`agent-os/standards/ux/trust-through-transparency.md:69`).
- `testing/validate-generated-artifacts`: **PASS** — quality test validates generated report JSON against `BenchmarkReport` schema (`tests/quality/benchmark/test_benchmark_quality.py:169`; standard `agent-os/standards/testing/validate-generated-artifacts.md:10`).

## Regression Check
- Recurring regression persists from prior audits: progress monotonicity remains unresolved (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:50`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:54`, `services/rentl-cli/src/rentl_cli/main.py:1417`).
- Round-4 Fix Now items remain open: dead `_run_benchmark_async` placeholder path still exists (`services/rentl-cli/src/rentl_cli/main.py:2590`), quality winner assertions still check candidate names (`tests/quality/benchmark/test_benchmark_quality.py:214`), and integration suite still lacks mocked end-to-end `benchmark compare` flow (`tests/integration/benchmark/test_cli_command.py:94`, `tests/features/benchmark/cli_command.feature:8`).
- Resolved signposts were not reopened without new evidence (Task 3 parser/hash/slice fixes remain implemented) (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:12`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:6`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:8`).

## Action Items

### Fix Now
- Make benchmark compare progress monotonic under out-of-order completion by tracking completed-task count (not task index) and add regression coverage for staggered completion (`services/rentl-cli/src/rentl_cli/main.py:1417`, `tests/integration/benchmark/test_cli_command.py:1`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`).
- Remove dead monolithic `_run_benchmark_async` placeholder path to satisfy Task 7 cleanup contract (`services/rentl-cli/src/rentl_cli/main.py:2590`, `services/rentl-cli/src/rentl_cli/main.py:2695`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`).
- Update quality winner assertions to enforce `HeadToHeadResult` labels `A|B|tie` instead of candidate names (`tests/quality/benchmark/test_benchmark_quality.py:214`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:30`).
- Add mocked BDD integration coverage for full `rentl benchmark compare` CLI flow (load outputs, line-ID validation, judge invocation, report write) to satisfy Task 7/8 integration contract (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:108`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:112`, `tests/integration/benchmark/test_cli_command.py:94`).

### Deferred
- None.
