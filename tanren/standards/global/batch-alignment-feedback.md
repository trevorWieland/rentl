# Batch Alignment Feedback

Any agent processing multiple items must verify output IDs match input IDs and provide structured retry feedback on mismatch.

## Rule

After a batch agent returns results, check:

1. **No missing IDs** — Every input ID appears in the output
2. **No extra IDs** — No output IDs that weren't in the input
3. **No duplicates** — Each output ID appears exactly once

On mismatch, build a feedback message listing the exact discrepancies and retry.

## Feedback Format

```python
def _alignment_feedback(input_ids: list[str], output_ids: list[str]) -> str | None:
    expected = set(input_ids)
    actual = set(output_ids)
    missing = expected - actual
    extra = actual - expected
    duplicates = [id for id in output_ids if output_ids.count(id) > 1]

    if not missing and not extra and not duplicates:
        return None

    parts = []
    if missing:
        parts.append(f"Missing IDs: {sorted(missing)}")
    if extra:
        parts.append(f"Extra IDs: {sorted(extra)}")
    if duplicates:
        parts.append(f"Duplicate IDs: {sorted(set(duplicates))}")
    parts.append("Return EXACTLY one output per input ID with no extras or omissions.")
    return "\n".join(parts)
```

## Why

LLMs processing batches frequently drop items, duplicate results, or hallucinate extra entries. Structured feedback gives the model specific correction instructions instead of a generic "try again", improving retry success rates.
