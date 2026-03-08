---
standard: llm-output-tolerance
category: python
score: 100
importance: High
violations_count: 0
date: 2026-02-17
status: clean
---

# Standards Audit: LLM Output Tolerance

**Standard:** `python/llm-output-tolerance`
**Date:** 2026-02-17
**Score:** 100/100
**Importance:** High

## Summary

The codebase enforces `extra="ignore"` at the shared schema base level and applies that base broadly across schema definitions, so LLM output parsing is tolerant to unexpected fields and avoids unnecessary retries. I did not find any schema that explicitly opts into strict/forbid extras for LLM-facing output paths. No real violations were identified against this standard.

## Violations

No violations found.

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/base.py:16` — `BaseSchema` sets `extra="ignore"` in shared `model_config`, establishing global tolerance for LLM-output extras.
- `packages/rentl-schemas/src/rentl_schemas/llm.py:22` — LLM runtime schema `LlmEndpointTarget(BaseSchema)` inherits the tolerant base configuration.
- `packages/rentl-core/src/rentl_core/benchmark/judge.py:28` — `JudgeOutput(BaseModel)` does not override extras, so it does not introduce `extra="forbid"` that would reject extra LLM fields.
- `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17` — `HeadToHeadResult(BaseModel)` also avoids explicit extra-forbid configuration, preserving permissive parsing of extra fields.

## Scoring Rationale

- **Coverage:** 100% of discovered schema classes are either based on `BaseSchema` (which enforces `extra="ignore"`) or do not explicitly forbid extras for parsed structured output.
  - `rg` found 118 `BaseSchema` subclasses and 13 `BaseModel` classes in the schema-related Python modules.
- **Severity:** No high/critical violations found; no schema was found with explicit `extra="forbid"` where it would block LLM outputs.
- **Trend:** Current codebase consistently applies the tolerant schema pattern across modules.
- **Risk:** Practical risk from this standard is low in scope because the code path most sensitive to extra fields is already tolerant.
