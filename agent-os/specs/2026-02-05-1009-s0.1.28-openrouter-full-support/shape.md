spec_id: s0.1.28
issue: https://github.com/trevorWieland/rentl/issues/112
version: v0.1

# Shape: OpenRouter Full Support

## Summary
Ensure OpenRouter and any OpenResponses/OpenAI-style endpoint behave with full feature parity vs local models. Switching providers should be seamless, tool calling should be reliable, and failures should be transparent and actionable.

## Problem
OpenRouter integration is currently brittle. Local models work, but switching to OpenRouter introduces failures (tool calling and structured output reliability). This blocks non-local users and undermines BYOK parity.

## Goals
- Full parity across local, OpenRouter, and any OpenResponses/OpenAI-compatible endpoint.
- Seamless switching via config without runtime or prompt changes.
- Reliable tool calling and structured outputs for all providers.
- Clear, transparent errors and telemetry on provider-specific failures.

## Non-Goals
- Adding provider-specific features beyond OpenResponses compatibility.
- Reworking prompts or agent logic unrelated to tool/output reliability.
- Changing the overall BYOK config structure.

## Constraints
- First-party support: must work reliably for non-local users.
- Must preserve async-first, strict typing, and pydantic-only schemas.

## Scope
- Provider detection and runtime configuration should be unified across agents and LLM runtime.
- Output mode selection must be deterministic and compatible with OpenRouter and local models.
- Tool usage must work across providers without requiring profile changes.
- Test coverage must prove parity and stability (unit + integration).

## Success Criteria
- Switching between local, OpenRouter, and other OpenResponses endpoints requires only config changes.
- Agents complete with tool calls and structured outputs across providers without runtime errors.
- Error messages clearly indicate provider limitations or misconfiguration.
- Tests cover provider routing, output mode decisions, and tool-call success paths.

## Risks
- Provider differences in tool calling and response formats may require precise compatibility handling.
- Mis-detection of provider types can cause incorrect output mode selection.

## Open Questions
- Any additional OpenResponses endpoints to prioritize for validation beyond OpenRouter?
