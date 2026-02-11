spec_id: s0.1.37
issue: https://github.com/trevorWieland/rentl/issues/37
version: v0.1

# Spec: Benchmark Harness v0.1

## Problem

rentl claims to produce better translations than raw machine translation, but there is no automated way to prove it. Without a benchmark harness, quality claims are anecdotal and untestable. The project needs a curated evaluation pipeline that downloads source material, compares competing translation outputs head-to-head using an LLM judge, and produces structured ranking reports.

## Goals

- Provide `rentl benchmark` CLI subcommands: `download` (fetch eval set) and `compare` (judge translation outputs)
- Download and parse eval set scripts (starting with Katawa Shoujo KSRE) at runtime
- Compare any two or more rentl run outputs head-to-head — the "MTL baseline" is simply a rentl run with only the translate phase enabled
- Use all-pairs comparison: for N candidates, run N*(N-1)/2 pairwise head-to-head judgments with randomized presentation order
- Score per-dimension (accuracy, style fidelity, consistency) and overall winner per line with reasoning
- Produce a structured Pydantic report with per-line rankings, pairwise win rates, and Elo ratings
- Language-agnostic — source/target language comes from eval set config and project config, not hardcoded
- Make the benchmark user-facing — runnable by end users, not just developers

## Non-Goals

- Full-game benchmark runs in CI (too slow; CI uses a narrow slice only)
- Automated pass/fail assertion that rentl beats MTL (quality tests validate mechanics, not outcomes)
- Publishing benchmark results or transparency packs (that's s0.1.38)
- Supporting eval sets beyond Katawa Shoujo in this spec (extensible design, but only one set implemented)
- Web UI for benchmark results (CLI-only for v0.1)
- Isolated absolute scoring (1-5 per line in isolation) — head-to-head comparison only

## Acceptance Criteria

- [ ] `rentl benchmark download --eval-set <name>` CLI subcommand downloads eval set source material, parses to rentl-ingestable format, and validates against committed SHA-256 hashes
- [ ] `rentl benchmark compare <output-a> <output-b> [output-c ...]` CLI subcommand takes two or more rentl run output paths and produces a comparison report
- [ ] All-pairs head-to-head judging: for N inputs, the judge runs N*(N-1)/2 pairwise comparisons with randomized A/B presentation order to avoid position bias
- [ ] Per-line judge output includes per-dimension winners (accuracy, style fidelity, consistency) and overall winner with reasoning, allowing ties
- [ ] Structured benchmark report uses Pydantic models with per-line head-to-head results + reasoning, pairwise win rates per dimension and overall, and Elo ratings
- [ ] The benchmark is language-agnostic — no hardcoded source/target language assumptions; language info comes from the eval set and translation outputs
- [ ] Benchmark quality test runs on a narrow slice with real LLMs, validating that judge comparison mechanics return proper per-line results with reasoning
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No committed copyrighted text** — Evaluation source text must be downloaded/parsed at runtime, never checked into the repo. Only configs, rubrics, and hashes are committed.
2. **Apples-to-apples comparison** — All translation outputs must be evaluated by the same judge model using the same rubric on the same source lines. The benchmark validates that all outputs cover the same line IDs before judging.
3. **Scores must include per-line evidence** — Aggregate rankings alone are insufficient. Each compared line must include the judge's reasoning so results can be audited.
4. **Benchmark must be runnable standalone** — Users can run `rentl benchmark download` and `rentl benchmark compare` without the full test suite, CI, or dev environment. These are first-class CLI commands, not pytest fixtures.
