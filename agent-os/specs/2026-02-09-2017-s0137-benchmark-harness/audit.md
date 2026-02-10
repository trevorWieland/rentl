status: fail
fix_now_count: 4

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 4

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 4/5
- Completion: 2/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — eval content is downloaded at runtime from KSRE (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:33`); committed eval-set artifacts are hash/slice config only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`; `git ls-files packages/rentl-core/src/rentl_core/benchmark/eval_sets`).
2. **Apples-to-apples comparison**: **PASS** — compare validates identical line IDs across candidates before judging (`services/rentl-cli/src/rentl_cli/main.py:1313`, `packages/rentl-core/src/rentl_core/benchmark/output_loader.py:67`) and uses one shared judge runtime/model configuration for all candidate pairs (`services/rentl-cli/src/rentl_cli/main.py:1329`, `services/rentl-cli/src/rentl_cli/main.py:1365`).
3. **Scores must include per-line evidence**: **PASS** — reasoning is required by schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`), required by judge response parsing (`packages/rentl-core/src/rentl_core/benchmark/judge.py:129`), and retained in report line-level results (`packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:51`).
4. **Benchmark must be runnable standalone**: **PASS** — standalone CLI commands are present (`services/rentl-cli/src/rentl_cli/main.py:1099`, `services/rentl-cli/src/rentl_cli/main.py:1228`), and `uv run rentl benchmark --help` lists `download` and `compare`.

## Demo Status
- Latest run: **PASS** (Run 5, 2026-02-10; `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:56`)
- Result quality: convincing for current environment constraints — Step 1 executed, Steps 2-5 are explicitly skipped with external-service rationale and quality-test substitution (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:57`).
- Full verification gate rerun in this audit: `make all` passed (format/lint/type + unit/integration/quality).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark tests are under unit/integration/quality tier paths (`tests/unit/benchmark/test_output_loader.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`; standard `agent-os/standards/testing/three-tier-test-structure.md:3`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality benchmark path invokes real CLI compare flow (no mocked judge runtime in the quality test file) (`tests/quality/benchmark/test_benchmark_quality.py:134`; standard `agent-os/standards/testing/no-mocks-for-quality-tests.md:41`).
- `testing/bdd-for-integration-quality`: **PASS** — benchmark integration and quality suites use Given/When/Then BDD steps (`tests/integration/benchmark/test_cli_command.py:32`, `tests/quality/benchmark/test_benchmark_quality.py:66`; standard `agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark contracts are Pydantic `BaseModel` definitions (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`; standard `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — compare path uses async/await with structured concurrency (`services/rentl-cli/src/rentl_cli/main.py:1273`, `services/rentl-cli/src/rentl_cli/main.py:1420`; standard `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — schema fields are explicitly typed and use `Field(description=...)` (`packages/rentl-schemas/src/rentl_schemas/benchmark/config.py:62`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`; standard `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **violation (Medium)** — progress accounting is index-based (`progress.update(... completed=index + 1)`), which can regress under out-of-order completion (`services/rentl-cli/src/rentl_cli/main.py:1417`), conflicting with progress visibility expectations (`agent-os/standards/ux/trust-through-transparency.md:69`).
- `testing/validate-generated-artifacts`: **PASS** — quality benchmark report output is validated against the consuming schema (`tests/quality/benchmark/test_benchmark_quality.py:169`; standard `agent-os/standards/testing/validate-generated-artifacts.md:10`).

## Regression Check
- Unresolved signpost remains unfixed: non-monotonic progress accounting (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`, `services/rentl-cli/src/rentl_cli/main.py:1417`).
- Prior spec-audit Fix Now issues are still present: stale dead `_run_benchmark_async` path (`services/rentl-cli/src/rentl_cli/main.py:2590`) and winner-label mismatch in quality assertions (`tests/quality/benchmark/test_benchmark_quality.py:214`).
- Resolved signposts were not reopened without new evidence: Task 3 parser/hash/slice fixes remain implemented (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:12`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:6`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:8`).

## Action Items

### Fix Now
- Make benchmark compare progress monotonic under out-of-order async completion by tracking completed-task count (not task index), and add regression coverage for staggered completion order (`services/rentl-cli/src/rentl_cli/main.py:1417`, `tests/integration/benchmark/test_cli_command.py:1`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`).
- Remove dead monolithic `_run_benchmark_async` placeholder path to satisfy Task 7 architecture cleanup contract (`services/rentl-cli/src/rentl_cli/main.py:2590`, `services/rentl-cli/src/rentl_cli/main.py:2695`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`).
- Update quality benchmark winner assertions to enforce schema contract values `A|B|tie` (not candidate names) so real-LLM quality runs validate actual compare semantics (`tests/quality/benchmark/test_benchmark_quality.py:214`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:30`).
- Add mocked integration coverage for full `rentl benchmark compare` CLI flow (load outputs, ID validation, judge invocation/report output) to satisfy Task 7/8 integration-test contract (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:108`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:112`, `tests/integration/benchmark/test_cli_command.py:94`).

### Deferred
- None.
