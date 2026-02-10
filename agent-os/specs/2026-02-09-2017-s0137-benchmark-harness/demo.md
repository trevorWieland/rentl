# Demo: Benchmark Harness v0.1

rentl now includes a benchmark harness that compares translation quality across different pipeline configurations and models. It downloads a curated evaluation set from Katawa Shoujo's KSRE scripts, and uses an LLM judge to perform all-pairs head-to-head comparisons between any two or more rentl run outputs. The judge scores per-dimension (accuracy, style fidelity, consistency) and overall winner per line with reasoning. Results are aggregated into pairwise win rates and Elo ratings to answer real-world questions like "Which model and method provides the best translation?"

## Steps

1. Run `rentl benchmark download --eval-set katawa-shoujo --slice demo` — expected: downloads eval set from KSRE GitHub, selects a small representative slice, shows line count and hash validation, writes rentl-ingestable source files

2. Run `rentl run` four times on the downloaded source using 2 models × 2 methods:
   - `openai/gpt-oss-20b` with full pipeline (context + translate + QA + edit)
   - `openai/gpt-oss-20b` with translate-only (no context, no QA, no edit)
   - `qwen/qwen3-vl-30b-a3b-instruct` with full pipeline
   - `qwen/qwen3-vl-30b-a3b-instruct` with translate-only
   - Expected: four output JSONL files produced, one per run

3. Run `rentl benchmark compare gpt-oss-full.jsonl gpt-oss-mtl.jsonl qwen3-full.jsonl qwen3-mtl.jsonl --judge-model <model> --candidate-names "gpt-oss-full,gpt-oss-mtl,qwen3-full,qwen3-mtl"` — expected: 6 pairwise head-to-head comparisons (C(4,2)=6) run with progress, randomized A/B presentation for each pair

4. Review the benchmark report — expected: per-line head-to-head results with reasoning for all 6 pairs, pairwise win rates per dimension, Elo ratings for all 4 candidates, overall ranking

5. Verify the report is coherent — expected: each compared line has per-dimension winners + overall winner + reasoning, win rates sum correctly, Elo ratings produce a consistent 4-candidate ranking, and the ranking answers "Which model and method provides the best translation?"

## Results

(Appended by run-demo — do not write this section during shaping)
