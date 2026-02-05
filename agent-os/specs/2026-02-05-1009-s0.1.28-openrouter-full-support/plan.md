spec_id: s0.1.28
issue: https://github.com/trevorWieland/rentl/issues/112
version: v0.1

# Plan: OpenRouter Full Support

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-05-1009-s0.1.28-openrouter-full-support/` with:
- **plan.md** — This full plan
- **shape.md** — Shaping notes (scope, decisions, context)
- **standards.md** — Relevant standards that apply
- **references.md** — Pointers to reference implementations studied
- **visuals/** — Any mockups or screenshots provided (none)

## Task 2: Audit provider routing, output modes, and tool usage

- Review provider detection logic in `packages/rentl-agents/src/rentl_agents/runtime.py` and
  `packages/rentl-llm/src/rentl_llm/openai_runtime.py`.
- Map current behavior for OpenRouter vs OpenAI vs local endpoints (output_mode auto selection,
  tool gating, required_tool_calls flow).
- Identify mismatches between agent runtime and BYOK runtime provider detection or model settings.

## Task 3: Centralize provider detection + capability mapping

- Add a shared helper for provider detection and capability flags (tool_choice support,
  response_format support, native structured output) in a shared module
  (e.g. `packages/rentl-llm/src/rentl_llm/providers.py` or `packages/rentl-agents/src/rentl_agents/providers.py`).
- Use this helper across agent runtime and BYOK runtime to keep provider handling consistent.
- Ensure detection uses base_url normalization (OpenRouter, localhost, OpenAI default).

## Task 4: Normalize auto output mode selection

- Update `ProfileAgent` output_mode auto-selection in
  `packages/rentl-agents/src/rentl_agents/runtime.py` to use capability mapping.
- Enforce clear errors when an explicit output_mode is incompatible with the provider.
- Keep auto mode deterministic and provider-safe (no hidden fallbacks).

## Task 5: Ensure tool-call reliability across providers

- Confirm tools are available and callable in all output modes (prompted/tool/native).
- Verify `required_tool_calls` gating does not block tool availability on prompted output.
- Add or adjust runtime safeguards when OpenRouter or local models ignore tool naming.

## Task 6: Bring OpenAI-compatible runtime to OpenRouter parity

- Update `packages/rentl-llm/src/rentl_llm/openai_runtime.py` to select
  `OpenRouterProvider` when base_url targets OpenRouter.
- Ensure model settings (timeouts, tokens, reasoning effort) remain consistent across providers.

## Task 7: Improve provider-specific errors + telemetry

- Update provider mismatch errors in `packages/rentl-agents/src/rentl_agents/runtime.py`
  to include provider name and guidance (e.g., recommended output mode or endpoint fix).
- Ensure telemetry/log messages are actionable and do not leak secrets.

## Task 8: Tests for provider parity + switching behavior

- Unit tests in `tests/unit/rentl-agents/test_profile_agent_execute.py`:
  - Output_mode auto selection uses capability mapping.
  - Explicit incompatible output_mode raises clear error.
- Integration tests in `tests/integration/byok/test_openai_runtime.py`:
  - OpenRouter base_url selects OpenRouter provider.
  - Provider switching via endpoint_ref remains config-only.
- Quality harness checks in `tests/quality/agents/quality_harness.py`:
  - OpenRouter base_url uses OpenRouter provider and tool calling remains enabled.

## Task 9: Verification - Run make all

Run `make all` to ensure all code passes quality checks:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests
- Run integration tests
- Run quality tests

This task MUST pass before the spec is considered complete. Failures must be fixed and re-run
until `make all` passes.

## Acceptance Checks

- OpenRouter and local models both execute agents with tools enabled and structured outputs validated.
- Switching providers only requires config changes (no prompt/profile edits).
- Output mode auto-selection is deterministic and provider-compatible.
- Provider errors are explicit and actionable in logs/telemetry.
- Tests cover provider detection, output mode decisions, and tool-call success paths.
