# LLM Output Tolerance

Schemas that receive LLM output must use `extra="ignore"` to tolerate extra fields. Config and internal schemas may be strict.

## Rule

- **LLM-output schemas** (agent results, tool outputs) — Use `extra="ignore"`. LLMs frequently add unrequested fields (explanations, metadata). Rejecting these causes unnecessary retries.
- **Config/internal schemas** — May use `extra="forbid"` to catch typos and invalid fields early.

## Current State

`BaseSchema` applies `extra="ignore"` globally (`packages/rentl-schemas/src/rentl_schemas/base.py`). This is intentional for now — all schemas inherit LLM tolerance. Future work may split into `LlmSchema(extra="ignore")` and `StrictSchema(extra="forbid")`.

## Why

LLMs are unreliable about output structure. A model asked for `{"summary": "..."}` might return `{"summary": "...", "reasoning": "I chose this because..."}`. Rejecting that wastes an API call and retry budget on a correct answer with bonus context.
