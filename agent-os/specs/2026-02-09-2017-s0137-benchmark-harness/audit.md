status: fail
fix_now_count: 4

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 1

## Rubric Scores (1-5)
- Performance: 3/5
- Intent: 4/5
- Completion: 2/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — eval-set repo contents are downloaded at runtime (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:33`), and tracked eval-set artifacts are hashes/slices only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`; `git ls-files packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/*` returned only those two files).
2. **Apples-to-apples comparison**: **PASS** — compare validates matching line IDs before judging (`services/rentl-cli/src/rentl_cli/main.py:1306`, `services/rentl-cli/src/rentl_cli/main.py:1308`) and uses one judge model/runtime configuration for all candidates in a run (`services/rentl-cli/src/rentl_cli/main.py:1324`, `services/rentl-cli/src/rentl_cli/main.py:1351`).
3. **Scores include per-line evidence**: **PASS** — per-line reasoning is required in schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`) and response parsing (`packages/rentl-core/src/rentl_core/benchmark/judge.py:129`), and all per-line results are persisted in report output (`services/rentl-cli/src/rentl_cli/main.py:1434`).
4. **Benchmark runnable standalone**: **PASS** — first-class CLI subcommands are present for `download` and `compare` (`services/rentl-cli/src/rentl_cli/main.py:1099`, `services/rentl-cli/src/rentl_cli/main.py:1228`).

## Demo Status
- Latest run: **PASS** (Run 2, 2026-02-10)
- `demo.md` records Step 1 as passing and Steps 2-5 as skipped due external API/runtime constraints (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:32`). This is acceptable per run-demo protocol, but fallback quality evidence is currently not reliable because the benchmark quality test fails when env is configured (see Fix Now #1).

## Standards Adherence
- `testing/three-tier-test-structure`: **violation (High)** — quality benchmark scenario does not execute successfully when quality env is present; it fails during fixture creation with schema validation errors (`tests/quality/benchmark/test_benchmark_quality.py:73`, `tests/quality/benchmark/test_benchmark_quality.py:74`, `tests/quality/benchmark/test_benchmark_quality.py:82`; repro: `set -a; source .env; set +a; pytest -q tests/quality/benchmark/test_benchmark_quality.py` → `ValidationError` for `line_id`/`scene_id`). Rule reference: quality tier must validate real LLM behavior (`agent-os/standards/testing/three-tier-test-structure.md:35`).
- `testing/no-mocks-for-quality-tests`: **PASS** — benchmark quality test invokes CLI and does not mock LLM runtime (`tests/quality/benchmark/test_benchmark_quality.py:134`).
- `testing/bdd-for-integration-quality`: **PASS** — integration and quality benchmark tests are BDD-wired via `scenarios(...)` and Given/When/Then steps (`tests/integration/benchmark/test_cli_command.py:20`, `tests/quality/benchmark/test_benchmark_quality.py:34`).
- `python/pydantic-only-schemas`: **PASS** — benchmark schemas are Pydantic models with `Field(...)` metadata (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`, `packages/rentl-schemas/src/rentl_schemas/benchmark/config.py:59`).
- `python/async-first-design`: **violation (Medium)** — compare path is async but executes line judging sequentially (`await` inside nested loops), not structured concurrent evaluation (`services/rentl-cli/src/rentl_cli/main.py:1388`, `services/rentl-cli/src/rentl_cli/main.py:1391`). Rule reference: use structured concurrency for async I/O (`agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — benchmark schema fields are explicitly typed and use `Field(description=...)` (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/config.py:62`).
- `ux/trust-through-transparency`: **PASS** — compare/download provide explicit progress and actionable errors (`services/rentl-cli/src/rentl_cli/main.py:1287`, `services/rentl-cli/src/rentl_cli/main.py:1363`, `services/rentl-cli/src/rentl_cli/main.py:1317`).
- `testing/validate-generated-artifacts`: **PASS** — report artifact is validated against `BenchmarkReport` schema in quality path (`tests/quality/benchmark/test_benchmark_quality.py:170`).

## Regression Check
- Audit-log shows repeated benchmark test/CLI drift across rounds, especially Task 4/5/8 cleanup loops (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:28`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:31`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:85`).
- Task 8 was marked resolved with a claim that quality comparison mechanics were validated, but new direct run with configured env now fails immediately on invalid fixture IDs before any LLM comparison, indicating unresolved regression risk (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:85`; failing command output cited above).

## Action Items

### Fix Now
- Repair benchmark quality BDD test so it runs end-to-end with real LLM config and schema-valid sample outputs (`tests/quality/benchmark/test_benchmark_quality.py:73`, `tests/quality/benchmark/test_benchmark_quality.py:74`, `tests/quality/benchmark/test_benchmark_quality.py:82`).
- Align `benchmark compare` candidate naming CLI to spec/demo (`--candidate-names` behavior and parsing) to match user-facing contract (`services/rentl-cli/src/rentl_cli/main.py:1235`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:16`; repro with `uv run rentl benchmark compare a.jsonl b.jsonl --candidate-names a,b`).
- Parallelize per-line judge comparisons in compare flow to meet async-first/throughput expectations (`services/rentl-cli/src/rentl_cli/main.py:1388`, `services/rentl-cli/src/rentl_cli/main.py:1391`).
- Remove stale pre-revision monolithic `_run_benchmark_async` placeholder path (`services/rentl-cli/src/rentl_cli/main.py:2569`, `services/rentl-cli/src/rentl_cli/main.py:2675`; task contract reference `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`).

### Deferred
- None.
