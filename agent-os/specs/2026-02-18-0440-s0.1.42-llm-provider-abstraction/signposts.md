# Signposts: LLM Provider Abstraction & Agent Wiring

## Signpost 1: `_resolve_reasoning_effort` crashes on plain string input

- **Task:** Demo Step 4 — Run a single BYOK prompt via the CLI with OpenRouter (Task 9)
- **Status:** `resolved`
- **Problem:** `AttributeError: 'str' object has no attribute 'value'` in `_resolve_reasoning_effort` at `packages/rentl-llm/src/rentl_llm/provider_factory.py:488`
- **Evidence:**
  - Expected: successful BYOK prompt response from OpenRouter
  - Actual: `rentl validate-connection` fails with `'str' object has no attribute 'value'`
  - `BaseSchema` uses `use_enum_values=True` (confirmed via `BaseSchema.model_config`), which causes Pydantic to store `StrEnum` members as plain strings
  - `LlmModelSettings.reasoning_effort` field stores `'medium'` (plain `str`) even when assigned `ReasoningEffort.MEDIUM`
  - `_resolve_reasoning_effort` at line 488 calls `effort.value`, assuming `effort` is a `ReasoningEffort` enum instance
  - Unit tests only pass `ReasoningEffort` enum instances, never plain strings — test gap
- **Root cause:** `_resolve_reasoning_effort` does not handle the case where `reasoning_effort` arrives as a plain string due to Pydantic's `use_enum_values=True` setting. The function signature says `ReasoningEffort | None` but the actual runtime type from Pydantic models is `str | None`.
- **Solution:** Updated `_resolve_reasoning_effort` to accept `ReasoningEffort | str | None`, using `isinstance` check to handle both enum and plain string inputs. Updated type annotations on `create_model`, `_create_openrouter_model`, and `_create_openai_model` accordingly. Added two unit tests covering plain string input for both OpenRouter and OpenAI paths.
- **Resolution:** do-task Task 9 (2026-02-18)
- **Files affected:**
  - `packages/rentl-llm/src/rentl_llm/provider_factory.py:480-494` — `_resolve_reasoning_effort` function
  - `tests/unit/llm/test_provider_factory.py` — added plain string `reasoning_effort` tests

## Signpost 2: Local model server not available for demo step 5

- **Task:** Demo Step 5 — Run BYOK prompt via CLI with local model (`RENTL_LOCAL_API_KEY`, `openai/gpt-oss-20b`)
- **Status:** `deferred`
- **Problem:** `httpx.ConnectError: All connection attempts failed` when connecting to `localhost:5000`
- **Evidence:**
  - Expected: successful BYOK response from local model server at `localhost:5000`
  - Actual: connection refused — no local model server running
  - Factory routing confirmed correct: `create_model()` produced `OpenAIChatModel` (not OpenRouter) for non-OpenRouter URL
  - Unit tests for OpenAI routing path pass (5/5): `test_openai_url_creates_openai_model`, `test_local_url_creates_openai_model`, `test_openai_includes_reasoning_effort`, `test_openai_reasoning_effort_plain_string`, `test_compatible_openai_endpoint_passes`
  - demo.md environment section states "local model server running" but the server is not running in the current environment
- **Root cause:** Environment prerequisite not met — the local model server (`openai/gpt-oss-20b` at `localhost:5000`) is not running. This is an infrastructure/environment issue, not a code defect. The factory code correctly routes non-OpenRouter URLs to `OpenAIChatModel`.
- **Files affected:** None — no code changes needed. Environment setup required.
