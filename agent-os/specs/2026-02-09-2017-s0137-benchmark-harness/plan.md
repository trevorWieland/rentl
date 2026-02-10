spec_id: s0.1.37
issue: https://github.com/trevorWieland/rentl/issues/37
version: v0.1

# Plan: Benchmark Harness v0.1

## Decision Record

rentl needs to prove its quality claims with data, not anecdotes. The benchmark harness downloads Katawa Shoujo scripts from the KSRE GitHub repo at runtime (Japanese source + English reference), generates both an MTL baseline and a full rentl pipeline translation, then uses an LLM-as-judge to score both on a rubric. The harness supports reference-based scoring (against the known-good English original), reference-free scoring, and head-to-head comparison. It is exposed as a first-class `rentl benchmark` CLI command usable by end users, not just developers. CI quality tests validate the judging mechanics on a narrow slice without asserting rentl beats MTL (that's validated manually on full runs).

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit and push spec artifacts on issue branch

- [x] Task 2: Benchmark schemas and rubric models
  - Create `rentl-schemas/src/rentl_schemas/benchmark/` module
  - Pydantic models: `BenchmarkConfig`, `EvalSetConfig`, `SliceConfig`
  - Rubric models: `RubricDimension`, `RubricScore` (1-5 scale with reasoning)
  - Score models: `LineScore` (per-line scores across dimensions), `HeadToHeadResult` (winner + reasoning)
  - Report model: `BenchmarkReport` (per-line scores, per-dimension aggregates, head-to-head win rates, overall comparison)
  - Support `scoring_mode: Literal["reference_based", "reference_free"]` in config
  - All models use `Field(description=...)` with strict typing, no `Any`
  - Unit tests for schema validation, serialization round-trips

- [x] Task 3: Eval set downloader and parser
  - Create `rentl-core/src/rentl_core/benchmark/eval_sets/` module
  - `KatawaShoujoDownloader`: fetch `.rpy` script files from KSRE GitHub repo via raw URLs or git archive
  - `RenpyDialogueParser`: parse Ren'Py `.rpy` files into `SourceLine` format (extract speaker, dialogue text, scene_id, line_id)
  - `LineAligner`: align English↔Japanese line pairs by scene/line ID
  - Hash validation: SHA-256 manifest file committed to repo, validated after download
  - Slice definitions: `demo` slice (~20-30 lines with dialogue, narration, choices, multiple speakers) defined in committed config
  - Async download with progress reporting
  - Unit tests: parser logic (mock `.rpy` content), hash validation, slice selection
  - Integration tests: mocked HTTP download, end-to-end parse flow
  - [x] Fix: Add committed Katawa Shoujo eval-set artifacts (config + SHA-256 manifest + `demo` slice definition) and wire Task 3 loader code to consume them; no benchmark eval-set config/manifest files were added in this task (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/` contains only Python modules) (audit round 1)
  - [x] Fix: Enforce manifest coverage for every requested script during download; current logic silently accepts files missing a manifest entry because hash comparison only runs when `expected_hash` is truthy (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:65`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:82`) (audit round 1)
  - [x] Fix: Normalize/derive schema-valid IDs when `scene_id` is omitted so KSRE filenames parse successfully; current default uses raw stem and fails `SourceLine` validation for names like `script-a1-sunday.rpy` (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py:38`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/parser.py:51`) (audit round 1)
  - [x] Fix: Add missing slice-selection unit coverage promised by Task 3 (`testing/three-tier-test-structure`); current unit tests only cover downloader/parser/aligner (`tests/unit/benchmark/eval_sets/test_downloader.py:1`, `tests/unit/benchmark/eval_sets/test_parser.py:1`, `tests/unit/benchmark/eval_sets/test_aligner.py:1`) (audit round 1)
  - [x] Fix: Add integration coverage for end-to-end download -> parse flow (`testing/three-tier-test-structure`); current integration suite only exercises downloader and never imports parser/aligner (`tests/integration/benchmark/eval_sets/test_download_flow.py:12`) (audit round 1)
  - [x] Fix: Replace placeholder empty-file SHA-256 values in `manifest.json` with real KSRE script hashes; current committed hashes (`e3b0...`) fail runtime validation and break downloader flow (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:6`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:92`) (audit round 2, see signposts.md: Task 3, manifest hash mismatch)
  - [x] Fix: Update `demo` slice to include the required content mix (dialogue, narration, choices, multiple speakers) and add test coverage that asserts those content properties for the configured slice (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:8`, `tests/unit/benchmark/eval_sets/test_loader.py:21`) (audit round 2, see signposts.md: Task 3, demo slice content mismatch)

- [ ] Task 4: MTL baseline generator
  - Create `rentl-core/src/rentl_core/benchmark/mtl_baseline.py`
  - Minimal translation prompt: "Translate the following Japanese text to English:" + source text
  - No context injection, no QA, no edit phases — raw single-shot LLM translation
  - Uses configured model endpoint (same model as rentl pipeline for fair comparison)
  - Async execution with concurrency limits and progress reporting
  - Output: list of `TranslatedLine` (same schema as pipeline output for apples-to-apples)
  - Unit tests: prompt construction, output schema validation
  - Integration tests: mocked LLM, validates correct prompt structure

- [ ] Task 5: Rubric judge implementation
  - Create `rentl-core/src/rentl_core/benchmark/judge.py`
  - `RubricJudge` class with configurable judge model (separate from translation model)
  - Three rubric dimensions scored 1-5:
    - **Accuracy**: faithfulness to source meaning (does the translation convey what the original says?)
    - **Style fidelity**: natural target-language expression, character voice preservation, register appropriateness
    - **Consistency**: terminology consistency, naming consistency across lines
  - Reference-based mode: judge prompt includes source + reference + candidate
  - Reference-free mode: judge prompt includes source + candidate only
  - Head-to-head mode: judge sees source + both candidates (labels "Translation A" / "Translation B", randomized assignment), picks winner per dimension + overall with reasoning
  - Per-line structured output with `RubricScore` per dimension
  - Async execution with concurrency limits
  - Unit tests: prompt construction, score parsing, randomization logic
  - Integration tests: mocked judge LLM, validates structured output extraction

- [ ] Task 6: Benchmark report generator
  - Create `rentl-core/src/rentl_core/benchmark/report.py`
  - Aggregate per-line `RubricScore` into per-dimension mean/median/stddev
  - Head-to-head win rates per dimension and overall
  - `BenchmarkReport` builder that assembles all results into the Pydantic report model
  - JSON serialization for programmatic consumption
  - Human-readable summary formatter for CLI output (table or structured text)
  - Unit tests: aggregation math, report construction, formatting

- [ ] Task 7: `rentl benchmark` CLI command
  - Add `benchmark` command to CLI router in `rentl-cli`
  - Wire together: download eval set → generate MTL baseline → run rentl pipeline → judge both → generate report
  - CLI flags:
    - `--eval-set` (required): eval set name (e.g., `katawa-shoujo`)
    - `--slice` (optional): slice name (e.g., `demo`) for subset evaluation
    - `--judge-model` (optional): override judge model ID
    - `--judge-base-url` (optional): override judge endpoint
    - `--scoring-mode` (optional): `reference-based` or `reference-free` (default: `reference-based` when reference available)
    - `--output` (optional): path to write JSON report
  - Progress output: download status, baseline progress, pipeline progress, judging progress, report summary
  - Error handling: missing API keys, download failures, judge failures
  - Integration tests: mocked end-to-end flow via CLI

- [ ] Task 8: Tests (unit + integration + quality)
  - Unit tests: all schema validation, parser logic, aggregation math, prompt construction
  - Integration tests (mocked LLM): full benchmark CLI flow, eval set download + parse, MTL baseline generation, judge wiring, report output
  - Quality test (real LLMs): run benchmark on demo slice, assert judge returns per-line scores with reasoning for all rubric dimensions, assert report structure is complete (no assertion on rentl beating MTL)
  - BDD feature files for integration and quality tiers
  - All tests within tier timing limits (unit <250ms, integration <5s, quality <30s)
