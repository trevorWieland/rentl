# Quality Agent Evals

This doc explains how to run the real-LLM quality evals for the five phase
agents (context, pretranslation, translate, QA, edit).

## Prerequisites

Quality tests use real LLM calls. All configuration is required via env vars
loaded from `.env` (if present) or your shell:

- `RENTL_QUALITY_API_KEY`
- `RENTL_QUALITY_BASE_URL`
- `RENTL_QUALITY_MODEL`
- `RENTL_QUALITY_JUDGE_MODEL`
- `RENTL_QUALITY_JUDGE_BASE_URL`

Notes:
- Keys are only read from env vars and are never logged.
- Quality evals are expected to complete in under 30 seconds per test.

## Running Quality Evals

Run the full quality suite:

```bash
make quality
```

Run a single agent eval:

```bash
uv run pytest tests/quality/agents/test_context_agent.py -q
```

## What the Evals Check

- Structured output validity (schema fields present)
- Tool call usage and output formatting
- Language correctness via LLM-as-judge rubrics
- Basic task expectations with lenient thresholds (initial baseline)

If a test fails, prefer prompt/profile improvements or runtime adjustments
over blaming the model. The goal is consistent behavior across strong and
weaker models.
