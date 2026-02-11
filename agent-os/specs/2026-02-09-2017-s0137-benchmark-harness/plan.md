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
  - [x] Fix: Align benchmark compare candidate naming interface to spec/demo by supporting `--candidate-names` and documented input format instead of only `--candidate-name` (`services/rentl-cli/src/rentl_cli/main.py:1235`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:16`; repro: `uv run rentl benchmark compare a.jsonl b.jsonl --candidate-names a,b` → `No such option`)
  - [x] Fix: Parallelize per-line judge calls in benchmark compare to satisfy async-first benchmark evaluation (current nested loop awaits each line sequentially at `services/rentl-cli/src/rentl_cli/main.py:1388` and `services/rentl-cli/src/rentl_cli/main.py:1391`; standard: `agent-os/standards/python/async-first-design.md:39`) (audit round 1)
    - [x] Fix: Correct comparison progress accounting to track completed-task count rather than task index; current `progress.update(task, completed=index + 1)` can regress and finish below 100% when tasks complete out of order (`services/rentl-cli/src/rentl_cli/main.py:1417`) (audit round 1)
    - [x] Fix: Add regression coverage for out-of-order async completion in benchmark compare progress reporting (mock staggered judge responses and assert monotonic completion to total) (`services/rentl-cli/src/rentl_cli/main.py:1413`, `tests/integration/benchmark/test_cli_command.py`) (audit round 1)
  - [x] Fix: Remove stale `_run_benchmark_async` monolithic placeholder path from pre-revision architecture (`services/rentl-cli/src/rentl_cli/main.py:2590`, `services/rentl-cli/src/rentl_cli/main.py:2695`; task contract: `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`) (audit round 1)

- [x] Task 8: Tests (unit + integration + quality)
  - Unit tests: all schema validation, output loading, pairwise aggregation, Elo math, prompt construction
  - Integration tests (mocked LLM): full `rentl benchmark compare` CLI flow, `rentl benchmark download` flow
  - Quality test (real LLMs): run comparison on demo slice outputs, assert judge returns per-line results with reasoning for all rubric dimensions, assert report structure is complete
  - BDD feature files for integration and quality tiers
  - All tests within tier timing limits (unit <250ms, integration <5s, quality <30s)
  - Clean up stale test files from old architecture (old CLI command tests, MTL baseline features)
  - Note: Quality test updated to head-to-head N-way architecture in do-task round 10
  - [x] Fix: Repair benchmark quality BDD test so it executes with real LLM config and schema-valid sample outputs (currently fails before compare with `TranslatedLine` validation errors at `tests/quality/benchmark/test_benchmark_quality.py:73`, `tests/quality/benchmark/test_benchmark_quality.py:74`, and `tests/quality/benchmark/test_benchmark_quality.py:82`; repro: `set -a; source .env; set +a; pytest -q tests/quality/benchmark/test_benchmark_quality.py`)
    - [x] Fix: Pass an API key env var accepted by benchmark compare when the quality test invokes CLI (currently only `RENTL_QUALITY_API_KEY` is passed, but CLI requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`, so the test exits before judge calls) (`tests/quality/benchmark/test_benchmark_quality.py:161`, `services/rentl-cli/src/rentl_cli/main.py:1315`) (audit round 1; see signposts.md Task 8 quality env-var mismatch)
  - [x] Fix: Align benchmark quality winner assertions with `HeadToHeadResult` contract (`A|B|tie`) instead of candidate-name labels so real-LLM quality runs validate actual compare output (`tests/quality/benchmark/test_benchmark_quality.py:214`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:30`) (audit round 2)
  - [x] Fix: Add mocked BDD integration coverage for the full `rentl benchmark compare` CLI flow (output loading, line-ID validation, judging, and report write) to satisfy Task 7/8 integration-test contract (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:108`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:112`, `tests/integration/benchmark/test_cli_command.py:94`) (audit round 4)
  - [x] Fix: Convert benchmark eval-set download integration coverage to BDD Given/When/Then scenarios (feature-backed) instead of direct pytest integration tests to satisfy integration-tier BDD requirements (`tests/integration/benchmark/eval_sets/test_download_flow.py:17`, `agent-os/standards/testing/bdd-for-integration-quality.md:3`) (audit round 7)
  - [x] Fix: Make the real-LLM benchmark quality scenario pass with the project OpenRouter config by using an OpenRouter-compatible judge model identifier (provider-qualified or config-derived) and verify the compare command no longer exits with `Unexpected error: not enough values to unpack (expected 2, got 1)` (`tests/quality/benchmark/test_benchmark_quality.py:152`, `services/rentl-cli/src/rentl_cli/main.py:1602`; repro: `set -a; source .env; set +a; uv run pytest -q tests/quality/benchmark/test_benchmark_quality.py`) (audit round 11)

- [x] Task 9: Fix eval-set name normalization
  - Add kebab-case to snake_case normalization in `_benchmark_download_async` so CLI accepts `--eval-set katawa-shoujo` (user-facing format)
  - Normalize before passing to `EvalSetLoader.load_manifest()` and `EvalSetLoader.load_slices()`
  - Update demo.md to use correct `--eval-set katawa-shoujo` format (kebab-case)
  - Add integration test: `rentl benchmark download --eval-set katawa-shoujo --slice demo` succeeds
  - Verify existing unit tests still pass (they use snake_case directly in Python, which is fine)

- [x] Task 10: Use project endpoint config for benchmark compare judge
  - **Critical**: `_benchmark_compare_async` hardcodes `os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")` at `services/rentl-cli/src/rentl_cli/main.py:1320` — must use the codebase's endpoint config system instead
  - **Remove** hardcoded API key checks (`main.py:1319-1326`)
  - **Remove** hardcoded `provider_name="openai"` and `api_key_env="OPENAI_API_KEY"` (`main.py:1334`, `main.py:1336`)
  - **Remove** hardcoded defaults `gpt-4o-mini` and `https://api.openai.com/v1` (`main.py:1329-1330`)
  - **Remove** hardcoded `max_output_tokens=2000` (`main.py:1342`) — must be configurable or derived from model defaults
  - **Add** `--config` option to `benchmark compare` to read judge endpoint from `rentl.toml` (same pattern as `run-pipeline`)
  - **Add** `--judge-api-key-env` option as override for judge API key env var name
  - **Load** `.env` via `_load_dotenv(config_path)` like `run-pipeline` does
  - **Resolve** API key from `endpoint.api_key_env` in config, not hardcoded provider names
  - **Detect** provider type from `--judge-base-url` using `detect_provider()` from `rentl_agents.providers`
  - **Include** `openrouter_provider` config (with `require_parameters=True`) when the judge endpoint is OpenRouter — currently the hardcoded `LlmEndpointTarget` at `main.py:1332-1337` has no `openrouter_provider`, so OpenRouter routing constraints are not applied to judge requests
  - Update integration tests to use configurable endpoint
  - Update quality test to use project endpoint config
  - Update demo.md Step 3 to include `--config` flag
  - [x] Fix: Make `--judge-base-url`/`--judge-api-key-env` override mode independent of config loading; `_benchmark_compare_async` still unconditionally calls `_load_resolved_config(config_path)` at `services/rentl-cli/src/rentl_cli/main.py:1333` and fails early when config is missing (repro: `Unexpected error: Config not found: /tmp/.../missing.toml`) (audit round 1; see signposts.md Task 10 override-mode config dependency)
  - [x] Fix: Remove remaining hardcoded judge defaults by deriving from config/default model settings (or explicit CLI options) instead of fixed `"gpt-4o-mini"`/`4096` at `services/rentl-cli/src/rentl_cli/main.py:1371`, `services/rentl-cli/src/rentl_cli/main.py:1420`, and `services/rentl-cli/src/rentl_cli/main.py:1434` (audit round 1)
  - [x] Fix: Update benchmark compare integration tests to validate config-driven endpoint resolution and override-mode behavior; current coverage still only injects `OPENAI_API_KEY` with no `--config` in `tests/integration/benchmark/test_cli_command.py:320` and `tests/integration/benchmark/test_cli_command.py:420` (audit round 1)
  - [x] Fix: Update quality benchmark test to use project endpoint config (`--config`) instead of only `--judge-base-url` + direct `OPENAI_API_KEY` injection (`tests/quality/benchmark/test_benchmark_quality.py:152`, `tests/quality/benchmark/test_benchmark_quality.py:160`) (audit round 1)
  - [x] Fix: Update demo Step 3 command to include `--config` per Task 10 contract (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:16`) (audit round 1)
  - [x] Fix: Repair new override-mode BDD scenarios to provide a `ctx` fixture; `pytest -q tests/integration/benchmark/test_cli_command.py` fails with `fixture 'ctx' not found` for `tests/features/benchmark/cli_command.feature:38` and `tests/features/benchmark/cli_command.feature:44` because steps require `ctx` in `tests/integration/benchmark/test_cli_command.py:525` and `tests/integration/benchmark/test_cli_command.py:562` (audit round 2)
  - [x] Fix: Remove remaining hardcoded judge token budget in compare runtime settings; `services/rentl-cli/src/rentl_cli/main.py:1454` still sets `max_output_tokens=4096` instead of deriving from config/default model settings or explicit CLI options per Task 10 contract (see signposts.md: Task 10 endpoint-config migration) (audit round 2)
  - [x] Fix: Add missing BDD step binding for `Then the command exits with status 1` so override-mode scenario runs end-to-end; currently `pytest -q tests/integration/benchmark/test_cli_command.py` fails with `StepDefinitionNotFoundError` at `tests/features/benchmark/cli_command.feature:41` because only status-2 binding exists in `tests/integration/benchmark/test_cli_command.py:82` (audit round 3; see signposts.md: Task 10 BDD step-binding regression)
  - [x] Fix: Remove override-mode dependency on undefined `config` when resolving OpenRouter behavior in compare runtime (`services/rentl-cli/src/rentl_cli/main.py:1461`-`services/rentl-cli/src/rentl_cli/main.py:1464` currently dereference `config.endpoint` outside config-based mode and crash with `Unexpected error: cannot access local variable 'config' where it is not associated with a value`; repro: `RENTL_OPENROUTER_API_KEY=dummy uv run rentl benchmark compare <a.jsonl> <b.jsonl> --judge-base-url https://openrouter.ai/api/v1 --judge-model test-model --judge-api-key-env RENTL_OPENROUTER_API_KEY`) (audit round 9)
  - [x] Fix: Add BDD integration regression coverage for OpenRouter override mode so `benchmark compare` validates `--judge-base-url https://openrouter.ai/api/v1` without requiring config-mode variables and preserves `openrouter_provider.require_parameters` behavior (`tests/integration/benchmark/test_cli_command.py`, `tests/features/benchmark/cli_command.feature`) (audit round 9)
  - [x] Fix: Detect duplicate candidate names before storing outputs in `_benchmark_compare_async`; currently `outputs[name] = lines` at `services/rentl-cli/src/rentl_cli/main.py:1312` silently overwrites earlier entries when multiple paths resolve to the same name (e.g., `dir1/output.jsonl` and `dir2/output.jsonl` without `--candidate-names`), which can drop a candidate and produce incorrect rankings (PR #120 feedback from @chatgpt-codex-connector[bot], feedback round 1)

- [x] Task 11: Rewrite judge to use pydantic-ai Agent (replace hand-rolled LLM protocol)
  - **Root cause**: The judge uses a custom `LlmRuntimeProtocol` + `LlmPromptRequest` abstraction with hand-rolled JSON parsing, fallback strategies, and retry logic. This is the wrong approach. The normal rentl pipeline already solved this problem cleanly using pydantic-ai `Agent` with `output_type`, which handles structured output enforcement, validation, and retries automatically across all model families.
  - **What must change**:
    1. Replace `LlmRuntimeProtocol`/`LlmPromptRequest` with pydantic-ai `Agent[None, JudgeOutput]` using `output_type=JudgeOutput` — this is the proven pattern from `rentl_agents/runtime.py:472-499`
    2. Use pydantic-ai model setup (OpenRouterModel/OpenAIChatModel + provider) matching the pattern in `rentl_agents/runtime.py:412-439`
    3. **Delete** `_extract_json_from_text` (4-layer JSON extraction fallback) — pydantic-ai structured output eliminates this entirely
    4. **Delete** `_parse_head_to_head` (dual-format text parser with legacy `dimension_winners` support) — `result.output` is already a validated `JudgeOutput`
    5. **Delete** the retry-on-parse-failure loop with `asyncio.sleep` backoff — pydantic-ai's `output_retries` handles this
    6. **Keep** `JudgeOutput` schema (already correct), A/B randomization logic, batch parallelization, and `HeadToHeadResult` assembly
    7. **Keep** the semaphore-based concurrency limit for rate limiting
  - **Constructor change**: `RubricJudge.__init__` should accept model config (model_id, base_url, api_key, provider type) instead of `LlmRuntimeProtocol` + `LlmRuntimeSettings` + raw api_key. It creates the pydantic-ai model/provider internally.
  - **compare_head_to_head simplification**: Build prompt → `agent.run(prompt)` → `result.output` is `JudgeOutput` → map to `HeadToHeadResult`. No JSON extraction, no format detection, no manual validation.
  - Update `services/rentl-cli/src/rentl_cli/main.py` to construct `RubricJudge` with model config instead of `LlmRuntimeProtocol`
  - Update unit tests: mock `Agent.run` instead of `LlmRuntimeProtocol.run_prompt`, remove all JSON-parsing and fallback-format tests
  - Update integration tests: verify end-to-end flow with mocked pydantic-ai agent
  - **Why this works**: pydantic-ai already handles structured output across OpenAI, OpenRouter, and compatible providers. It negotiates `response_format`, validates against the Pydantic schema, and retries on malformed output. This is battle-tested across all translation phases (context, pretranslation, translate, QA, edit).
  - **Previous attempts (all superseded)**: Rounds 15-18 tried to fix the hand-rolled approach by adding structured output to `LlmPromptRequest`, 4-layer JSON extraction, dual format support, explicit dimension fields, and fallback alignment. Each fix introduced new edge cases. The correct solution is to stop using the custom protocol entirely.
  - [x] Fix: Add presentation-order metadata to `HeadToHeadResult` (e.g., `presented_as_a: str` field recording which candidate the judge saw as "A") so reasoning text referencing A/B labels can be correctly interpreted during audits; currently `reasoning` at `packages/rentl-core/src/rentl_core/benchmark/judge.py:231` is raw judge text with A/B labels in the judge's presentation frame, but `winner`/`dimension_winners` are remapped to canonical order, creating contradictory per-line records when randomization swaps the order (PR #120 feedback from @chatgpt-codex-connector[bot], feedback round 1)

- [x] Task 12: Reconcile demo.md steps with actual CLI capabilities
  - Demo Steps 2-5 reference `rentl run` which doesn't exist (the command is `run-pipeline`)
  - Demo Step 3 doesn't include `--config` flag needed after Task 10
  - Demo should document the full end-to-end flow with correct commands and working model/endpoint config
  - Update acceptance criteria if needed

- [x] Task 13: Fix eval set to download Japanese translations (not English originals)
  - **Root cause**: KSRE is "Katawa Shoujo: Re-Engineered", a modernization of the originally-English VN. Main `game/` scripts are English. Japanese translations are at `game/tl/jp/`.
  - **Change `KSRE_RAW_BASE`** in `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13` from `game` to `game/tl/jp`
  - **Update `RenpyDialogueParser`** in `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py` to handle Ren'Py translation file format (`translate` blocks mapping English→Japanese) instead of original script dialogue format
  - **Recompute SHA-256 hashes** for the Japanese translation files and update `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json`
  - **Update slice line ranges** in `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json` — the Japanese translation files have different line counts and structure than the English originals
  - **Update unit tests** for parser (translation file format), downloader (new URL path), loader (new hashes/slices)
  - **Clear cached files** at `~/.cache/rentl/eval_sets/katawa-shoujo/` (stale English scripts)
  - Verify: `uv run rentl benchmark download --eval-set katawa-shoujo --slice demo` produces Japanese text
  - Verify: all existing tests still pass with updated fixtures
  - [x] Fix: Update `RenpyDialogueParser._parse_translation_file` to correctly handle `translate <lang> strings:` blocks by parsing `new "..."` translations (and skipping `old "..."` source text), so English source strings are not emitted as benchmark source lines (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py:228`; repro: `speaker old`, `text Why?`) (audit round 1; see signposts.md: Task 13, translate-strings old/new leak)
  - [x] Fix: Add parser regression coverage for `translate ... strings:` old/new pairs asserting only translated `new` text is emitted (no `speaker=="old"` outputs), and add/update downloader unit coverage that validates the JP path contract (`game/tl/jp`) for Task 13 test-scope completeness (`tests/unit/benchmark/eval_sets/test_parser.py`, `tests/unit/benchmark/eval_sets/test_downloader.py`) (audit round 1)

- [ ] Task 14: Fix benchmark download to produce pipeline-ingestable JSONL
  - **Root cause**: `SourceLine.model_dump()` includes `source_columns: null`, but ingest adapter's `ALLOWED_KEYS` at `packages/rentl-io/src/rentl_io/ingest/jsonl_adapter.py:20` only allows `{line_id, route_id, scene_id, speaker, text, metadata}`
  - **Fix**: When writing download output JSONL, exclude `source_columns` from serialization (e.g., `line.model_dump(exclude={"source_columns"}, exclude_none=True)` or similar)
  - **Also ensure**: `route_id` is either omitted when None or populated with a valid value, since the ingest adapter may require it
  - **Add integration test**: `benchmark download` → `run-pipeline` ingest accepts the output without errors (test with mocked pipeline, just verify ingest parsing succeeds)
  - Verify: `uv run rentl benchmark download --eval-set katawa-shoujo --slice demo --output-dir /tmp/test && head -1 /tmp/test/*.jsonl` produces clean JSONL without `source_columns`
  - Verify: JSONL can be ingested by the pipeline without "unexpected fields" errors
  - [ ] Fix: Replace the synthetic JSONL ingestability scenario with an end-to-end CLI scenario that runs `rentl benchmark download` and ingests the generated file; current coverage manually serializes parsed lines at `tests/integration/benchmark/eval_sets/test_download_flow_bdd.py:520`, bypassing the benchmark download writer in `services/rentl-cli/src/rentl_cli/main.py:1208` (audit round 1)
  - [ ] Fix: In that CLI-backed scenario, assert generated records omit `source_columns` and omit `route_id` when null to enforce the ingest key contract at `packages/rentl-io/src/rentl_io/ingest/jsonl_adapter.py:20` (audit round 1)
