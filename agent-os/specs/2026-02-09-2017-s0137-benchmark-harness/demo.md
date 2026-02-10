# Demo: Benchmark Harness v0.1

rentl now includes a benchmark harness that proves the pipeline produces better translations than raw machine translation. It downloads a curated evaluation set from Katawa Shoujo's KSRE scripts (Japanese source + English reference), runs both a bare MTL baseline and the full rentl pipeline on a representative slice, then uses an LLM judge to score both on accuracy, style fidelity, and consistency.

## Steps

1. Run `rentl benchmark --eval-set katawa-shoujo --slice demo` — expected: downloads eval set from KSRE GitHub, selects a small representative slice (~20-30 lines with dialogue, narration, choices, multiple speakers), shows line count and hash validation
2. Observe MTL baseline + rentl pipeline running on the slice — expected: both complete within minutes, progress visible for each stage
3. Observe judge scoring — expected: both translations scored per-line on accuracy, style fidelity, and consistency with reasoning for each score
4. Review the benchmark report — expected: per-dimension scores (mean/median), head-to-head win rates, overall comparison. Report is structured Pydantic output (JSON).
5. Verify the report is coherent — expected: scores are numeric (1-5), reasoning is present for each line, aggregates are mathematically consistent
6. Confirm the harness is ready for a full-game run — expected: `rentl benchmark --eval-set katawa-shoujo` (no slice flag) would run the same logic on the full evaluation set

## Results

(Appended by run-demo — do not write this section during shaping)
