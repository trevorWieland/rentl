spec_id: s0.1.37
issue: https://github.com/trevorWieland/rentl/issues/37
version: v0.1

# Spec: Benchmark Harness v0.1

## Problem

rentl claims to produce better translations than raw machine translation, but there is no automated way to prove it. Without a benchmark harness, quality claims are anecdotal and untestable. The project needs a curated evaluation pipeline that downloads source material, generates competing translations, and uses an LLM judge to score them on a defined rubric.

## Goals

- Provide a `rentl benchmark` CLI command that runs an end-to-end quality comparison
- Download and parse Katawa Shoujo scripts from KSRE (Japanese source + English reference) at runtime
- Generate an MTL baseline (raw LLM translation without pipeline features) for comparison
- Score both translations using an LLM-as-judge on accuracy, style fidelity, and consistency
- Support both reference-based scoring (against known-good English original) and reference-free scoring
- Support head-to-head comparison mode with randomized presentation order
- Produce a structured Pydantic report with per-line scores, reasoning, and aggregate comparison
- Make the benchmark user-facing — runnable by end users, not just developers

## Non-Goals

- Full-game benchmark runs in CI (too slow; CI uses a narrow slice only)
- Automated pass/fail assertion that rentl beats MTL (quality tests validate mechanics, not outcomes)
- Publishing benchmark results or transparency packs (that's s0.1.38)
- Supporting eval sets beyond Katawa Shoujo in this spec (extensible design, but only one set implemented)
- Web UI for benchmark results (CLI-only for v0.1)

## Acceptance Criteria

- [ ] `rentl benchmark` CLI command exists and runs the full benchmark pipeline (download eval set, generate MTL baseline, run rentl pipeline, judge both, report results)
- [ ] Evaluation dataset downloader fetches Katawa Shoujo KSRE scripts from GitHub, parses to rentl SourceLine format, and validates against committed SHA-256 hashes
- [ ] MTL baseline generator translates evaluation lines with a minimal prompt (no context, no QA, no edit) using the configured model
- [ ] Rubric-based LLM judge scores both MTL and rentl translations on accuracy, style fidelity, and consistency using a configurable judge model with per-line reasoning
- [ ] Structured benchmark report uses Pydantic models with per-line scores + reasoning, per-dimension aggregates, and overall comparison (rentl vs MTL)
- [ ] Head-to-head comparison mode has the judge see both translations side-by-side (randomized order to avoid position bias) and pick a winner per line with reasoning
- [ ] Benchmark quality test runs on a narrow slice with real LLMs, validating that judge scoring mechanics return proper per-line scores with reasoning
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No committed copyrighted text** — Evaluation source text must be downloaded/parsed at runtime, never checked into the repo. Only configs, rubrics, and hashes are committed.
2. **Apples-to-apples comparison** — MTL baseline and rentl pipeline must be evaluated by the same judge model using the same rubric on the same source lines. No asymmetric evaluation.
3. **Scores must include per-line evidence** — Aggregate scores alone are insufficient. Each scored line must include the judge's reasoning so results can be audited.
4. **Benchmark must be runnable standalone** — Users can run `rentl benchmark` without the full test suite, CI, or dev environment. It's a first-class CLI command, not a pytest fixture.
