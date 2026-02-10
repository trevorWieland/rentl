status: fail
fix_now_count: 4

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 6

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 4/5
- Completion: 2/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — evaluation scripts are fetched from KSRE at runtime (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:79`), hash-validated (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:86`), and the repo only stores manifest/slice metadata (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`).
2. **Apples-to-apples comparison**: **PASS** — compare enforces matching line IDs across all candidates before judging (`services/rentl-cli/src/rentl_cli/main.py:1313`, `packages/rentl-core/src/rentl_core/benchmark/output_loader.py:67`) and uses one shared judge runtime/model config for all pairwise comparisons (`services/rentl-cli/src/rentl_cli/main.py:1329`, `services/rentl-cli/src/rentl_cli/main.py:1396`).
3. **Scores must include per-line evidence**: **PASS** — reasoning is required by schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`), enforced during judge-response parsing (`packages/rentl-core/src/rentl_core/benchmark/judge.py:129`), and persisted in report output (`packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:51`).
4. **Benchmark must be runnable standalone**: **PASS** — first-class CLI commands are registered and executable (`services/rentl-cli/src/rentl_cli/main.py:1099`, `services/rentl-cli/src/rentl_cli/main.py:1228`), independent of pytest/CI.

## Demo Status
- Latest run: **PASS** (Run 7, 2026-02-10; `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:72`).
- Results are acceptable for environment limits: Step 1 executed; Steps 2-5 were skipped with explicit external-service/runtime justification and mapped to quality-test verification (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:73`).
- Verification rerun in this audit: `make all` passed (unit/integration/quality gates green).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark tests exist in `tests/unit`, `tests/integration`, and `tests/quality` (`tests/unit/benchmark/test_output_loader.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`; standard `agent-os/standards/testing/three-tier-test-structure.md:3`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality benchmark scenario invokes real CLI compare and real endpoint config, not mocked judge calls (`tests/quality/benchmark/test_benchmark_quality.py:134`, `tests/quality/benchmark/test_benchmark_quality.py:142`; standard `agent-os/standards/testing/no-mocks-for-quality-tests.md:41`).
- `testing/bdd-for-integration-quality`: **PASS** — integration/quality benchmark tests use Given/When/Then with feature-backed scenarios (`tests/integration/benchmark/test_cli_command.py:32`, `tests/quality/benchmark/test_benchmark_quality.py:134`; standard `agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark rubric/report contracts are Pydantic models (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`; standard `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — compare path is async and uses structured concurrency (`services/rentl-cli/src/rentl_cli/main.py:1273`, `services/rentl-cli/src/rentl_cli/main.py:1420`; standard `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — benchmark schema fields are explicitly typed and use `Field(description=...)` (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:42`; standard `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **violation (Medium)** — progress is updated with task creation index (`services/rentl-cli/src/rentl_cli/main.py:1417`) instead of completion count, so out-of-order completion can regress visible progress (repro output: `updates [2, 3, 1]`, final `1` for `3` tasks). This violates progress visibility expectations (`agent-os/standards/ux/trust-through-transparency.md:69`).
- `testing/validate-generated-artifacts`: **PASS** — generated benchmark report is schema-validated via `BenchmarkReport.model_validate(...)` (`tests/quality/benchmark/test_benchmark_quality.py:169`; standard `agent-os/standards/testing/validate-generated-artifacts.md:10`).

## Regression Check
- Recurring unresolved pattern remains across audits: progress monotonicity keeps failing from Task 7 round 6 through Spec Audit rounds 2-5 (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:48`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:50`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:56`).
- Prior Fix Now items remain unaddressed with fresh evidence: dead `_run_benchmark_async` placeholder path still exists (`services/rentl-cli/src/rentl_cli/main.py:2590`), quality winner assertions still use candidate labels instead of `A|B|tie` (`tests/quality/benchmark/test_benchmark_quality.py:214`), and integration benchmark CLI coverage still omits mocked end-to-end compare flow (`tests/integration/benchmark/test_cli_command.py:94`).
- Resolved signposts were respected and not reopened without new evidence: Task 3 hash/slice fixes remain in place (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:6`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:8`; signposts `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:21`).

## Action Items

### Fix Now
- Make benchmark compare progress monotonic under out-of-order completion by tracking completed-task count (not task index) and add regression coverage for staggered completion (`services/rentl-cli/src/rentl_cli/main.py:1417`, `tests/integration/benchmark/test_cli_command.py:94`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`).
- Remove dead monolithic `_run_benchmark_async` placeholder path to satisfy Task 7 cleanup contract (`services/rentl-cli/src/rentl_cli/main.py:2590`, `services/rentl-cli/src/rentl_cli/main.py:2695`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`).
- Update quality winner assertions to enforce `HeadToHeadResult` labels `A|B|tie` instead of candidate names (`tests/quality/benchmark/test_benchmark_quality.py:214`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:30`).
- Add mocked BDD integration coverage for full `rentl benchmark compare` CLI flow (output loading, line-ID validation, judge invocation, report write) to satisfy Task 7/8 integration contract (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:108`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:112`, `tests/integration/benchmark/test_cli_command.py:94`).

### Deferred
- None.
