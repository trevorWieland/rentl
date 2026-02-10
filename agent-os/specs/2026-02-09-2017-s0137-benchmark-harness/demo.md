# Demo: Benchmark Harness v0.1

rentl now includes a benchmark harness that compares translation quality across different pipeline configurations. It downloads a curated evaluation set from Katawa Shoujo's KSRE scripts, and uses an LLM judge to perform head-to-head comparisons between any two or more rentl run outputs (e.g., a full-pipeline run vs a translate-only "MTL" run). The judge scores per-dimension (accuracy, style fidelity, consistency) and overall winner per line with reasoning. Results are aggregated into pairwise win rates and Elo ratings.

## Steps

1. Run `rentl benchmark download --eval-set katawa-shoujo --slice demo` — expected: downloads eval set from KSRE GitHub, selects a small representative slice, shows line count and hash validation, writes rentl-ingestable source files
2. Run `rentl run` twice with different configs on the downloaded source (full pipeline vs translate-only) — expected: two output JSONL files produced
3. Run `rentl benchmark compare output-full.jsonl output-mtl.jsonl --judge-model <model>` — expected: all-pairs head-to-head comparison runs with progress, randomized A/B presentation
4. Review the benchmark report — expected: per-line head-to-head results with reasoning, pairwise win rates per dimension, Elo ratings, overall ranking
5. Verify the report is coherent — expected: each compared line has per-dimension winners + overall winner + reasoning, win rates sum correctly, Elo ratings produce a ranking
6. Confirm N-way support — expected: `rentl benchmark compare a.jsonl b.jsonl c.jsonl` runs 3 pairwise comparisons and produces a 3-candidate ranking with Elo

## Results

(Appended by run-demo — do not write this section during shaping)
