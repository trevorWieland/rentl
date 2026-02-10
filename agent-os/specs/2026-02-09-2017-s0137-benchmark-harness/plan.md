spec_id: s0.1.37
issue: https://github.com/trevorWieland/rentl/issues/37
version: v0.1

# Plan: Benchmark Harness v0.1

## Decision Record

rentl needs to prove its quality claims with data, not anecdotes. The benchmark harness downloads evaluation source material (starting with Katawa Shoujo KSRE scripts) at runtime, then compares the outputs of separate rentl pipeline runs head-to-head using an LLM judge. The "MTL baseline" is not a separate component — it's simply a rentl run with only the translate phase enabled (no context, no QA, no edit). The harness uses all-pairs comparison: for N candidate outputs, it runs N*(N-1)/2 pairwise head-to-head judgments with randomized presentation order, scoring per-dimension (accuracy, style fidelity, consistency) and overall winner per line with reasoning. Results are aggregated into pairwise win rates and Elo ratings. The harness is language-agnostic and exposed as first-class `rentl benchmark download` and `rentl benchmark compare` CLI subcommands.

### Architecture Change (v0.1 revision)

The original design embedded pipeline execution inside the benchmark command and included a custom MTL baseline generator. This was architecturally wrong — the benchmark should compare outputs, not run pipelines. The revised design:

1. User runs `rentl run` with full config → output JSONL (the "rentl" candidate)
2. User runs `rentl run` with minimal config (translate-only) → output JSONL (the "MTL" candidate)
3. User runs `rentl benchmark compare <output-a> <output-b>` → head-to-head comparison report

This eliminates the pipeline integration blocker, removes the MTL baseline generator, and makes the benchmark a pure comparison tool. Isolated absolute scoring (1-5 per line) is dropped in favor of head-to-head comparison only, which is more reliable for subjective quality assessment.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit and push spec artifacts on issue branch
  - Note: spec.md revised via resolve-blockers (2026-02-10) to head-to-head-only N-way architecture

- [x] Task 2: Revise benchmark schemas for head-to-head N-way comparison
  - **Remove** from `rentl_schemas/benchmark/rubric.py`: `RubricScore`, `LineScore` (isolated scoring models)
  - **Keep** `RubricDimension` enum (accuracy, style_fidelity, consistency)
  - **Keep** `HeadToHeadResult` — already has `winner`, `reasoning`, `dimension_winners`; add `candidate_a_name` and `candidate_b_name` fields to track which candidates were compared
  - **Revise** `rentl_schemas/benchmark/report.py`:
    - Remove `DimensionAggregate`, `TranslationResult` (isolated scoring aggregates)
    - Revise `HeadToHeadSummary` to be per-pair: add `candidate_a_name`, `candidate_b_name`
    - Add `EloRating` model: `candidate_name: str`, `rating: float`
    - Revise `BenchmarkReport`: remove `mtl_result`/`rentl_result`/`scoring_mode`, add `candidates: list[str]`, `pairwise_results: list[PairwiseSummary]` (one per candidate pair), `elo_ratings: list[EloRating]`, `overall_ranking: list[str]`
  - **Revise** `rentl_schemas/benchmark/config.py`:
    - Remove `scoring_mode`, `head_to_head` from `BenchmarkConfig` (always head-to-head now)
    - Keep `EvalSetConfig`, `SliceConfig` as-is
  - Update `__init__.py` exports
  - Update unit tests: remove isolated scoring tests, add N-way schema validation
  - All models use `Field(description=...)` with strict typing, no `Any`

- [x] Task 3: Eval set downloader and parser
  - Existing work is valid and tested (downloader, parser, aligner, loader, manifest, slices)
  - No changes needed — `benchmark download` CLI will reuse this directly

- [x] Task 4: Output loader and dead code removal
  - **Create** `rentl-core/src/rentl_core/benchmark/output_loader.py`:
    - Read rentl run output JSONL files into `TranslatedLine` format
    - Support loading from export output paths (the files `rentl run` produces)
    - Validate that all candidate outputs cover the same set of line IDs
    - Raise clear errors when line ID sets don't match across candidates
  - **Remove** `rentl-core/src/rentl_core/benchmark/mtl_baseline.py` and all its tests:
    - `tests/unit/benchmark/test_mtl_baseline.py`
    - `tests/integration/benchmark/test_mtl_baseline_flow.py`
    - `tests/features/benchmark/mtl_baseline_generation.feature` (if exists)
  - Unit tests: output loading, line ID validation, error cases
  - [x] Fix: Remove stale `MTLBaselineGenerator` monkeypatch/setup from `tests/integration/benchmark/test_cli_command.py:179` and `tests/integration/benchmark/test_cli_command.py:186` (currently `pytest -q tests/integration/benchmark/test_cli_command.py` fails with `AttributeError: module 'rentl_cli.main' has no attribute 'MTLBaselineGenerator'`) (audit round 6)
  - [x] Fix: Eliminate commented placeholder benchmark dead code in `services/rentl-cli/src/rentl_cli/main.py:2338` through `services/rentl-cli/src/rentl_cli/main.py:2377` to satisfy Task 4 dead-code removal scope (audit round 6)
  - [x] Fix: Resolve Task 4 spillover that removed judge scoring APIs without test migration (`packages/rentl-core/src/rentl_core/benchmark/judge.py:154`; `tests/integration/benchmark/test_judge_flow.py:279`; `tests/integration/benchmark/test_judge_flow.py:289`) so Task 4 no longer leaves broken integration coverage (`pytest -q tests/integration/benchmark/test_judge_flow.py`) (audit round 6)
  - [x] Fix: Remove stale `RubricJudge` monkeypatch from `tests/integration/benchmark/test_cli_command.py:179` and `tests/integration/benchmark/test_cli_command.py:183` (`pytest -q tests/integration/benchmark/test_cli_command.py` currently fails with `AttributeError: module 'rentl_cli.main' has no attribute 'RubricJudge'`) (audit round 7; see signposts.md Task 4 stale CLI BDD mismatch)
  - [x] Fix: Align `tests/features/benchmark/cli_command.feature:6` and `tests/integration/benchmark/test_cli_command.py:329`/`tests/integration/benchmark/test_cli_command.py:489` with current benchmark command stub behavior in `services/rentl-cli/src/rentl_cli/main.py:1113`-`services/rentl-cli/src/rentl_cli/main.py:1115` so stale success/API-key assertions no longer fail the Task 4 benchmark CLI integration suite (audit round 7; see signposts.md Task 4 stale CLI BDD mismatch)

- [x] Task 5: Revise judge for pairwise-only comparison
  - **Remove** `score_translation` method (isolated scoring)
  - **Remove** reference-based/reference-free mode distinction from judge
  - **Keep and adapt** `compare_head_to_head` for pairwise use:
    - Source text is provided alongside both candidates for context
    - Rubric dimensions (accuracy, style fidelity, consistency) guide comparison
    - Judge picks per-dimension winner + overall winner with reasoning, ties allowed
    - Randomized A/B presentation order preserved
  - **Ensure** judge prompt includes source text so judge has context for accuracy evaluation
  - Update unit tests: remove isolated scoring tests, verify pairwise comparison
  - Update integration BDD tests: remove reference-based/reference-free scenarios, keep head-to-head scenarios
  - [x] Fix: Remove stale skipped isolated-scoring unit tests and dead calls to removed judge APIs (`_build_reference_based_prompt`, `_build_reference_free_prompt`, `_parse_rubric_scores`, `score_translation`, `score_batch`) from `tests/unit/benchmark/test_judge.py:63`, `tests/unit/benchmark/test_judge.py:88`, `tests/unit/benchmark/test_judge.py:135`, `tests/unit/benchmark/test_judge.py:163`, `tests/unit/benchmark/test_judge.py:189`, `tests/unit/benchmark/test_judge.py:276`, `tests/unit/benchmark/test_judge.py:314`, and `tests/unit/benchmark/test_judge.py:348` (audit round 3)
  - [x] Fix: Replace skip-based legacy coverage with active pairwise-only assertions in `tests/unit/benchmark/test_judge.py` so Task 5 test migration is complete and no longer relies on `pytest.mark.skip` placeholders for removed modes (audit round 3; see signposts.md Task 5 skipped legacy judge tests)

- [x] Task 6: Report generator — pairwise win rates and Elo
  - **Rewrite** `rentl-core/src/rentl_core/benchmark/report.py`:
    - Build per-pair `HeadToHeadSummary` from list of `HeadToHeadResult`
    - Compute pairwise win rates per dimension and overall
    - Implement Elo rating computation from pairwise head-to-head results
    - Derive overall ranking from Elo ratings
    - Assemble `BenchmarkReport` from all pairwise summaries + Elo
  - Human-readable summary formatter for CLI output (ranking table, win rates)
  - Unit tests: pairwise aggregation, Elo computation, report assembly, formatting
  - [x] Fix: Derive `overall_ranking` inside the report generator from Elo ratings instead of requiring caller-supplied ranking (`packages/rentl-core/src/rentl_core/benchmark/report.py:131`, `packages/rentl-core/src/rentl_core/benchmark/report.py:139`) (audit round 3)
  - [x] Fix: Handle zero-comparison pairwise summaries in `compute_elo_ratings` to prevent division by zero, and add a regression unit test (`packages/rentl-core/src/rentl_core/benchmark/report.py:116`; repro output: `ZeroDivisionError division by zero`) (audit round 3)

- [x] Task 7: `rentl benchmark` CLI subcommands
  - **Rewrite** benchmark CLI as two subcommands:
  - `rentl benchmark download`:
    - `--eval-set` (required): eval set name (e.g., `katawa-shoujo`)
    - `--slice` (optional): slice name for subset
    - `--output-dir` (optional): where to write parsed source files
    - Downloads, parses, validates hashes, writes rentl-ingestable source files
  - `rentl benchmark compare`:
    - Positional args: 2+ paths to rentl run output files
    - `--judge-model` (optional): override judge model ID
    - `--judge-base-url` (optional): override judge endpoint
    - `--output` (optional): path to write JSON report
    - `--candidate-names` (optional): human-readable names for each candidate (defaults to filenames)
    - Loads all outputs, validates matching line IDs, runs all-pairs head-to-head judging, generates report
  - **Remove** old monolithic `rentl benchmark` command and `_run_benchmark_async`
  - Progress output: comparison progress, report summary
  - Error handling: missing API keys, mismatched line IDs, file not found
  - Integration tests: mocked end-to-end flow via CLI subcommands

- [x] Task 8: Tests (unit + integration + quality)
  - Unit tests: all schema validation, output loading, pairwise aggregation, Elo math, prompt construction
  - Integration tests (mocked LLM): full `rentl benchmark compare` CLI flow, `rentl benchmark download` flow
  - Quality test (real LLMs): run comparison on demo slice outputs, assert judge returns per-line results with reasoning for all rubric dimensions, assert report structure is complete
  - BDD feature files for integration and quality tiers
  - All tests within tier timing limits (unit <250ms, integration <5s, quality <30s)
  - Clean up stale test files from old architecture (old CLI command tests, MTL baseline features)
  - Note: Quality test updated to head-to-head N-way architecture in do-task round 10

- [x] Task 9: Fix eval-set name normalization
  - Add kebab-case to snake_case normalization in `_benchmark_download_async` so CLI accepts `--eval-set katawa-shoujo` (user-facing format)
  - Normalize before passing to `EvalSetLoader.load_manifest()` and `EvalSetLoader.load_slices()`
  - Update demo.md to use correct `--eval-set katawa-shoujo` format (kebab-case)
  - Add integration test: `rentl benchmark download --eval-set katawa-shoujo --slice demo` succeeds
  - Verify existing unit tests still pass (they use snake_case directly in Python, which is fine)

- [x] Fix: Repair benchmark quality BDD test so it executes with real LLM config and schema-valid sample outputs (currently fails before compare with `TranslatedLine` validation errors at `tests/quality/benchmark/test_benchmark_quality.py:73`, `tests/quality/benchmark/test_benchmark_quality.py:74`, and `tests/quality/benchmark/test_benchmark_quality.py:82`; repro: `set -a; source .env; set +a; pytest -q tests/quality/benchmark/test_benchmark_quality.py`).
  - [x] Fix: Pass an API key env var accepted by benchmark compare when the quality test invokes CLI (currently only `RENTL_QUALITY_API_KEY` is passed, but CLI requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`, so the test exits before judge calls) (`tests/quality/benchmark/test_benchmark_quality.py:161`, `services/rentl-cli/src/rentl_cli/main.py:1315`) (audit round 1; see signposts.md Task 8 quality env-var mismatch)
- [x] Fix: Align benchmark compare candidate naming interface to spec/demo by supporting `--candidate-names` and documented input format instead of only `--candidate-name` (`services/rentl-cli/src/rentl_cli/main.py:1235`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:16`; repro: `uv run rentl benchmark compare a.jsonl b.jsonl --candidate-names a,b` → `No such option`).
- [x] Fix: Parallelize per-line judge calls in benchmark compare to satisfy async-first benchmark evaluation (current nested loop awaits each line sequentially at `services/rentl-cli/src/rentl_cli/main.py:1388` and `services/rentl-cli/src/rentl_cli/main.py:1391`; standard: `agent-os/standards/python/async-first-design.md:39`).
- [ ] Fix: Remove stale `_run_benchmark_async` monolithic placeholder path from pre-revision architecture (`services/rentl-cli/src/rentl_cli/main.py:2569`, `services/rentl-cli/src/rentl_cli/main.py:2675`; task contract: `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`).
