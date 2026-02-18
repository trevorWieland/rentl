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

### Run 2 — Post-Task-9-fix (2026-02-18 06:34)
- Step 1 [RUN]: PASS — All 33 factory unit tests pass (OpenRouter routing, OpenAI routing, model ID validation, allowlist enforcement, preflight checks, plain string reasoning_effort)
- Step 2 [RUN]: PASS — `validate_openrouter_model_id('invalid-no-slash')` raises `ProviderFactoryError` with clear `provider/model-name` format message
- Step 3 [RUN]: PASS — `enforce_provider_allowlist('google/gemma', only=['qwen'])` raises `ProviderFactoryError` listing allowed providers
- Step 4 [RUN]: PASS — Factory created `OpenRouterModel` from Pydantic config with plain string `reasoning_effort='medium'`; pydantic-ai Agent call to OpenRouter returned successful response (`"Hello!"`)
- Step 5 [RUN]: FAIL — Factory routing confirmed correct (`OpenAIChatModel` created for non-OpenRouter URL), but local model server at `localhost:5000` is not running — `httpx.ConnectError: All connection attempts failed`. Environment prerequisite not met (see signposts.md #2)
- Step 6 [RUN]: PASS — 12 tool-related unit tests pass; `_build_tool_list` returns `list[Tool]` with explicit names and descriptions preserved
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 910 unit, 91 integration, 9 quality)
- **Overall: FAIL**

### Run 3 — Post-audit-task-9 (2026-02-18 06:45)
- Step 1 [RUN]: PASS — All 33 factory unit tests pass (OpenRouter routing, OpenAI routing, model ID validation, allowlist enforcement, preflight checks, plain string reasoning_effort)
- Step 2 [RUN]: PASS — `validate_openrouter_model_id('invalid-no-slash')` raises `ProviderFactoryError` with clear `provider/model-name` format message
- Step 3 [RUN]: PASS — `enforce_provider_allowlist('google/gemma', OpenRouterProviderRoutingConfig(only=['qwen']))` raises `ProviderFactoryError` listing allowed providers
- Step 4 [RUN]: FAIL — Factory correctly creates `OpenRouterModel` with proper settings, but OpenRouter API returns 404 for all tested models with `require_parameters=true`. Error: "No endpoints found that can handle the requested parameters". Same model succeeds with `require_parameters=false` (factory returned `"Hello"` response). The `qwen` provider is also no longer available on OpenRouter (`available_providers: alibaba, deepinfra, novita, phala, siliconflow`; `requested_providers: qwen`). External service degradation, not a code defect. (see signposts.md #3)
- Step 5 [RUN]: FAIL — Local model server at `localhost:5000` not running (`curl --connect-timeout 5` fails). Same as run 2 (see signposts.md #2)
- Step 6 [RUN]: PASS — 12 tool-related unit tests pass; `_build_tool_list` returns `list[Tool]` with explicit names and descriptions preserved
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 910 unit, 91 integration, 9 quality)
- **Overall: FAIL**

### Run 4 — Post-audit-task-9-round-2 (2026-02-18 06:55)
- Step 1 [RUN]: PASS — All 33 factory unit tests pass (OpenRouter routing, OpenAI routing, model ID validation, allowlist enforcement, preflight checks, plain string reasoning_effort)
- Step 2 [RUN]: PASS — `validate_openrouter_model_id('invalid-no-slash')` raises `ProviderFactoryError` with clear `provider/model-name` format message
- Step 3 [RUN]: PASS — `enforce_provider_allowlist('google/gemma', OpenRouterProviderRoutingConfig(only=['qwen']))` raises `ProviderFactoryError` listing allowed providers
- Step 4 [RUN]: FAIL — Factory correctly creates `OpenRouterModel` with proper settings; verified end-to-end with `require_parameters=false` (Agent returned `"Hello"` via OpenRouter). With `require_parameters=true`, OpenRouter returns 404 for all models — same external service issue as run 3 (see signposts.md #3). `rentl validate-connection` runs without code errors but reports endpoint `status: failed`. Not a code defect.
- Step 5 [RUN]: FAIL — Local model server at `localhost:5000` not running (`curl --connect-timeout 5` fails). Same as runs 2-3 (see signposts.md #2). Factory routing confirmed correct via unit tests (5/5 OpenAI routing tests pass).
- Step 6 [RUN]: PASS — 12 tool-related unit tests pass; `_build_tool_list` returns `list[Tool]` with explicit names and descriptions preserved
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 910 unit, 91 integration, 9 quality)
- **Overall: FAIL**

### Run 5 — Post-audit-round-2 (2026-02-18 07:00)
- Step 1 [RUN]: PASS — All 33 factory unit tests pass (OpenRouter routing, OpenAI routing, model ID validation, allowlist enforcement, preflight checks, plain string reasoning_effort)
- Step 2 [RUN]: PASS — `validate_openrouter_model_id('invalid-no-slash')` raises `ProviderFactoryError` with clear `provider/model-name` format message
- Step 3 [RUN]: PASS — `enforce_provider_allowlist('google/gemma', only=['qwen'])` raises `ProviderFactoryError` listing allowed providers
- Step 4 [RUN]: FAIL — Factory correctly creates `OpenRouterModel`; raw HTTP to OpenRouter succeeds (200, `"Hello"` response), but pydantic-ai Agent request returns 404 because OpenRouter can't handle the additional parameters pydantic-ai sends. `rentl validate-connection` runs without code errors but reports endpoint `status: failed`. Same external service issue as runs 3-4 (see signposts.md #3). Not a code defect.
- Step 5 [RUN]: FAIL — Local model server at `localhost:5000` not running (`curl --connect-timeout 5` fails). Same as runs 2-4 (signpost #2). Factory routing confirmed correct via unit tests.
- Step 6 [RUN]: PASS — 12 tool-related unit tests pass; `_build_tool_list` returns `list[Tool]` with explicit names and descriptions preserved
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 910 unit, 91 integration, 9 quality)
- **Overall: FAIL**

### Run 6 — Post-audit-round-3 (2026-02-18 08:28)
- Step 1 [RUN]: PASS — All 33 factory unit tests pass (OpenRouter routing, OpenAI routing, model ID validation, allowlist enforcement, preflight checks, plain string reasoning_effort)
- Step 2 [RUN]: PASS — `validate_openrouter_model_id('invalid-no-slash')` raises `ProviderFactoryError` with clear `provider/model-name` format message
- Step 3 [RUN]: PASS — `enforce_provider_allowlist('google/gemma', only=['qwen'])` raises `ProviderFactoryError` listing allowed providers
- Step 4 [RUN]: FAIL — Factory correctly creates `OpenRouterModel`; direct factory call with `require_parameters=False` succeeds (Agent returned `"Hello"` via OpenRouter), but `require_parameters=True` still returns 404 from OpenRouter. `rentl validate-connection` runs without code errors but reports endpoint `status: failed`. Same external service issue as runs 3-5 (signpost #3). Not a code defect.
- Step 5 [RUN]: FAIL — Factory correctly routes to `OpenAIChatModel` for non-OpenRouter URL (confirmed). Local model server at `localhost:5000` still not running. Same as runs 2-5 (signpost #2). Environment prerequisite not met, not a code defect.
- Step 6 [RUN]: PASS — 15 tool-related unit tests pass; `_build_tool_list` returns `list[Tool]` with explicit names and descriptions preserved
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 910 unit, 91 integration, 9 quality)
- **Overall: FAIL**
