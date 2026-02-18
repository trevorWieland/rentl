# Signposts: LLM Provider Abstraction & Agent Wiring

## Signpost 1: `_resolve_reasoning_effort` crashes on plain string input

- **Task:** Demo Step 4 — Run a single BYOK prompt via the CLI with OpenRouter
- **Status:** `unresolved`
- **Problem:** `AttributeError: 'str' object has no attribute 'value'` in `_resolve_reasoning_effort` at `packages/rentl-llm/src/rentl_llm/provider_factory.py:488`
- **Evidence:**
  - Expected: successful BYOK prompt response from OpenRouter
  - Actual: `rentl validate-connection` fails with `'str' object has no attribute 'value'`
  - `BaseSchema` uses `use_enum_values=True` (confirmed via `BaseSchema.model_config`), which causes Pydantic to store `StrEnum` members as plain strings
  - `LlmModelSettings.reasoning_effort` field stores `'medium'` (plain `str`) even when assigned `ReasoningEffort.MEDIUM`
  - `_resolve_reasoning_effort` at line 488 calls `effort.value`, assuming `effort` is a `ReasoningEffort` enum instance
  - Unit tests only pass `ReasoningEffort` enum instances, never plain strings — test gap
- **Root cause:** `_resolve_reasoning_effort` does not handle the case where `reasoning_effort` arrives as a plain string due to Pydantic's `use_enum_values=True` setting. The function signature says `ReasoningEffort | None` but the actual runtime type from Pydantic models is `str | None`.
- **Files affected:**
  - `packages/rentl-llm/src/rentl_llm/provider_factory.py:480-488` — `_resolve_reasoning_effort` function
  - `tests/unit/llm/test_provider_factory.py` — missing test for plain string `reasoning_effort`
