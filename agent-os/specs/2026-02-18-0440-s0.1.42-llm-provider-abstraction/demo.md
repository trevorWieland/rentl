# Demo: LLM Provider Abstraction & Agent Wiring

This spec centralizes scattered LLM provider construction behind a single factory, adds validation and enforcement at config boundaries, and fixes agent tool registration to use typed objects. The demo proves the factory routes correctly, validation catches bad input, and the full pipeline still works end-to-end.

## Environment

- API keys: `RENTL_OPENROUTER_API_KEY` via `.env` (OpenRouter), `RENTL_LOCAL_API_KEY` via `.env` (local model server)
- External services: OpenRouter API reachable, local model server running (`openai/gpt-oss-20b`)
- Setup: none

## Steps

1. **[RUN]** Run unit tests for the new factory module — expected: all factory tests pass, covering OpenRouter routing, generic OpenAI routing, model ID validation, and allowlist enforcement.

2. **[RUN]** Attempt to load a config with an invalid model ID (e.g., `invalid-no-slash`) via a test script — expected: Pydantic validation error at parse time with a clear message about the required `provider/model` format.

3. **[RUN]** Attempt to load a config with an allowlisted provider violation (e.g., model `google/gemma` when only `qwen` is allowed) — expected: factory rejects with actionable error.

4. **[RUN]** Run a single BYOK prompt via the CLI with OpenRouter config (`RENTL_OPENROUTER_API_KEY`) — expected: successful response, logs confirm factory was used.

5. **[RUN]** Run a single BYOK prompt via the CLI with local model config (`RENTL_LOCAL_API_KEY`, `openai/gpt-oss-20b`) — expected: successful response, logs confirm factory routed to generic OpenAI provider.

6. **[RUN]** Verify `AgentFactory.resolve_tools` returns `pydantic_ai.Tool` objects — expected: unit tests confirm return type is `list[Tool]` with explicit names.

7. **[RUN]** Run `make all` — expected: full verification gate passes.

## Results

### Run 1 — Post-task-completion (2026-02-18 06:19)
- Step 1 [RUN]: PASS — All 31 factory unit tests pass (OpenRouter routing, OpenAI routing, model ID validation, allowlist enforcement, preflight checks)
- Step 2 [RUN]: PASS — Pydantic validation rejected `invalid-no-slash` at parse time with clear `provider/model-name` format error
- Step 3 [RUN]: PASS — Factory rejected `google/gemma` when only `qwen` is allowed, with actionable error listing allowed providers
- Step 4 [RUN]: FAIL — `rentl validate-connection` fails with `AttributeError: 'str' object has no attribute 'value'` in `_resolve_reasoning_effort` at `provider_factory.py:488`. Root cause: `BaseSchema` uses `use_enum_values=True` which stores `StrEnum` as plain strings, but `_resolve_reasoning_effort` assumes `ReasoningEffort` enum instances. Test gap: unit tests only pass enum instances, never plain strings.
- **Overall: FAIL**
