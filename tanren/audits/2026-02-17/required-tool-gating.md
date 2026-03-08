---
standard: required-tool-gating
category: global
score: 100
importance: High
violations_count: 0
date: 2026-02-18
status: clean
---

# Standards Audit: Required Tool Gating

**Standard:** `global/required-tool-gating`
**Date:** 2026-02-18
**Score:** 100/100
**Importance:** High

## Summary

The runtime path that executes profile-driven agents with tool lists applies output-tool gating only when required tool calls are explicitly configured, and it enforces exhaustive tool handling in that mode. Propagation of required tools from profile TOML into runtime config is consistently wired in `wiring.py`, and the compliance behavior is directly validated by unit tests. Other `Agent` call sites do not expose function tools or do not model required tool call semantics, so the standard is fully met in the checked code paths.

## Violations

No violations found.

## Compliant Examples

- `packages/rentl-agents/src/rentl_agents/runtime.py:471-505` — When `required_tool_calls` is set, runtime defines `prepare_output_tools`, updates `end_strategy` to `"exhaustive"`, and passes both into `Agent(...)`.
- `packages/rentl-agents/src/rentl_agents/wiring.py:334-341` — Required tools from agent profiles are propagated to runtime as `required_tool_calls`.
- `tests/unit/rentl-agents/test_profile_agent_execute.py:189-233` — Unit test confirms `prepare_output_tools` is non-`None` and `end_strategy` is `"exhaustive"` for required tools.

## Scoring Rationale

- **Coverage:** All relevant profile-driven agent execution paths that can require function tools now gate output tools via `prepare_output_tools`, and there are explicit tests covering that behavior.
- **Severity:** No violations found, so no corrective severity risk is present.
- **Trend:** Existing code and tests are internally consistent; the recent design appears coherent and intentional.
- **Risk:** No functional risk detected from this standard at present.
