spec_id: s0.1.28
issue: https://github.com/trevorWieland/rentl/issues/112
version: v0.1

# Plan: OpenRouter Full Support

## Objectives
- Deliver reliable OpenRouter + OpenResponses compatibility with full parity to local models.
- Ensure seamless provider switching via config only.
- Guarantee tool calling and structured output behavior across providers.

## Task List
1. Save Spec Documentation
2. Audit current provider routing, output mode selection, and tool usage in agent and LLM runtime layers.
3. Normalize provider detection and runtime configuration so OpenRouter and OpenResponses endpoints share consistent handling.
4. Harden output mode selection and tool-call reliability for OpenRouter and local models.
5. Improve error messages and telemetry for provider-specific failures.
6. Extend unit and integration tests to validate provider parity and switching behavior.
7. Update any configuration or validation notes needed for OpenRouter/OpenResponses endpoints.
8. Run `make all`.

## Acceptance Checks
- OpenRouter and local models both execute agents with tools enabled and structured outputs validated.
- Switching providers only requires config changes (no prompt/profile edits).
- Failure modes are explicit and actionable in logs/telemetry.
- Tests cover provider detection and output mode logic.
