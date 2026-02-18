---
standard: agent-tool-registration
category: global
score: 72
importance: High
violations_count: 2
date: 2026-02-17
status: violations-found
---

# Standards Audit: Agent Tool Registration

**Standard:** `global/agent-tool-registration`  
**Date:** 2026-02-17  
**Score:** 72/100  
**Importance:** High

## Summary

The codebase mostly routes tools through `Tool` wrappers in the runtime path, but not all construction paths do. `AgentFactory` still builds a raw callable list from `tool.execute` and forwards it into the harness, which can expose the wrong tool identity to the model (`execute`). The `AgentHarness` API also accepts/passes raw callables directly, which allows this mismatch pattern to persist from callers and tests. No explicit prompt-to-tool-name mismatch is evidenced in production prompt templates.

## Violations

### Violation 1: AgentFactory passes raw `tool.execute` callables into agent construction path

- **File:** `packages/rentl-agents/src/rentl_agents/factory.py:292`
- **Severity:** High
- **Evidence:**
  ```python
  tool_list = []
  ...
      tool = tool_factory()
      tool_list.append(tool.execute)
  ...
  agent = AgentHarness(..., tools=tool_callables)
  ```
- **Recommendation:** return wrapped `Tool` objects instead of raw callables, e.g. `tool_list.append(Tool(tool.execute, name=tool.name, description=tool.description, takes_ctx=False))`, or reuse `ToolRegistry.get_tool_callables(...)` directly.

### Violation 2: AgentHarness accepts and forwards raw callables to `pydantic_ai.Agent`

- **File:** `packages/rentl-agents/src/rentl_agents/harness.py:86`
- **Severity:** Medium
- **Evidence:**
  ```python
  tools: list[Callable[..., dict[str, JsonValue]]] | None = None
  ...
  agent: Agent[None, OutputT_co] = Agent[None, OutputT_co](
      ...
      tools=self._tools,
  )
  ```
- **Recommendation:** align the harness contract with the standard by changing tool typing/validation to `list[Tool]` and requiring explicit `Tool(name=..., description=..., takes_ctx=...)` registration before passing to `Agent`.

## Compliant Examples

- `packages/rentl-agents/src/rentl_agents/tools/registry.py:168` — uses explicit `Tool(tool.execute, name=tool.name, description=tool.description, takes_ctx=False)` when preparing tool callables.
- `packages/rentl-agents/src/rentl_agents/runtime.py:421` + `:501` — gets tool set from `ToolRegistry.get_tool_callables(...)` and passes that list into `Agent`.
- `tests/unit/rentl-agents/test_tool_registry.py:95` — validates that `get_tool_callables(...)` returns a `Tool` instance with expected `.name`.

## Scoring Rationale

- **Coverage:** 2 of 3 production tool-delivery paths are compliant with explicit `Tool` registration; one direct path in `AgentFactory` is not.
- **Severity:** One high-severity violation (identity mismatch risk via `tool.execute`) and one medium-severity contract mismatch in `AgentHarness`.
- **Trend:** No evidence of a migration to consistently enforce `Tool` objects across the whole factory/harness boundary.
- **Risk:** High practical impact in tool-based runs because duplicate/misaligned tool names can cause prompt-tool mismatches and unreliable tool-call behavior.
