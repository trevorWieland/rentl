# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

## Signpost 1: OpenRouter cost not accessible through pydantic-ai

- **Task:** 4
- **Status:** resolved
- **Problem:** pydantic-ai's `RunUsage` does not propagate OpenRouter's native cost data. OpenRouter includes cost in the API response `usage` object, but the OpenAI SDK's `CompletionUsage` Pydantic model doesn't define a `cost` field, so it's silently dropped during parsing. Additionally, pydantic-ai's `_map_usage()` function in `pydantic_ai/models/openai.py` filters the `details` dict to only include `int` values (line 2881: `if isinstance(v, int)`), which excludes any float cost values.
- **Evidence:**
  - `CompletionUsage` only has `completion_tokens`, `prompt_tokens`, `total_tokens` + detail sub-objects — no `cost` field
  - pydantic-ai `_map_usage` at line 2881: `if isinstance(v, int)` filters out floats
  - `genai_prices` has OpenRouter pricing data but spec non-negotiable #3 prohibits static pricing tables
- **Tried:** Investigated `RunUsage.details`, `RequestUsage.extract()`, `genai_prices.calc_price()`, OpenAI SDK's `CompletionUsage`
- **Solution:** Implemented config-based cost calculation via `input_cost_per_mtok` / `output_cost_per_mtok` fields on `ModelSettings`. When both are set, cost is computed as `(input_tokens * input_price + output_tokens * output_price) / 1M`. When neither is set, `cost_usd` is `None` (graceful degradation). The code is structured so that if pydantic-ai adds cost propagation in the future, it can be easily integrated.
- **Resolution:** do-task round 1 (Task 4)
- **Files affected:** `packages/rentl-agents/src/rentl_agents/runtime.py`, `packages/rentl-schemas/src/rentl_schemas/config.py`
