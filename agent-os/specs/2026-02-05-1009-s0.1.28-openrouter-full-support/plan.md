spec_id: s0.1.28
issue: https://github.com/trevorWieland/rentl/issues/112
version: v0.1

# Plan: OpenRouter Full Support

## Decision Record (Why This Refactor Exists)

Recent investigation found that reliability failures are not solved by model-specific hacks; they are architecture mismatches:

- Quality evals and production currently exercise different output paths.
- `output_mode="auto"` can route OpenRouter traffic to non-tool-first behavior.
- OpenRouter provider routing is heterogeneous; endpoints can differ on `tools` and `tool_choice` support.
- Rentl currently uses a generic OpenAI chat path for OpenRouter in key places, limiting use of OpenRouter-native routing controls.

Decision for this spec:

- Remove `auto`, `prompted`, and `native` from runtime behavior.
- Enforce tool output everywhere (`output_mode=tool` semantics only).
- Enforce OpenRouter provider parameter support (`require_parameters=true`) so routing excludes incompatible endpoints.
- Migrate OpenRouter calls to `OpenRouterModel` where available to use typed OpenRouter settings.
- Keep implementation provider-agnostic and strictly typed (no model hardcoding, no `Any`/`object`).

## Task 1: Update Spec Artifacts

- Update this plan with the tool-only strategy and migration rationale.
- Ensure `shape.md` and acceptance language no longer depends on mixed output modes.

## Task 2: Collapse Runtime to Tool-Only Output

- Refactor `packages/rentl-agents/src/rentl_agents/runtime.py` so agent execution always uses tool output.
- Remove `PromptedOutput` execution path and all output-mode branching in runtime logic.
- Preserve required-tool gating (`prepare_output_tools`) and `end_strategy="exhaustive"` behavior.
- Remove/replace `OutputMode` union values that are no longer valid.

## Task 3: Simplify Provider Capability Logic for Tool-Only

- Refactor `packages/rentl-agents/src/rentl_agents/providers.py`:
  - remove auto/prompted/native recommendation logic,
  - keep provider detection and tool-capability checks,
  - expose a tool-only compatibility assertion with actionable error text.
- Ensure detection handles OpenRouter/OpenAI/local/private-IP endpoints consistently.

## Task 4: Add Strictly-Typed OpenRouter Routing Settings in Config

- Extend `packages/rentl-schemas/src/rentl_schemas/config.py` with explicit OpenRouter provider routing schema fields (all `Field(..., description=...)`):
  - include `require_parameters` (default `true`),
  - optional routing controls such as `order`, `only`, `ignore`, `allow_fallbacks`, `sort`.
- Add validation so OpenRouter-only config is not accepted for non-OpenRouter endpoints.
- Ensure schema and validators follow `@agent-os/standards/python/strict-typing-enforcement.md`.

## Task 5: Propagate OpenRouter Settings Through Agent Wiring

- Extend `ProfileAgentConfig` in `packages/rentl-agents/src/rentl_agents/runtime.py` to carry typed OpenRouter routing settings.
- Update config assembly in `packages/rentl-agents/src/rentl_agents/wiring.py` and `scripts/validate_agents.py` to pass these settings from endpoint config to runtime.
- Remove CLI/config pathways for selecting non-tool output behavior.

## Task 6: Use OpenRouterModel for OpenRouter Endpoints

- Update agent runtime model selection in `packages/rentl-agents/src/rentl_agents/runtime.py`:
  - use `OpenRouterModel` for OpenRouter endpoints,
  - use `OpenAIChatModel` for non-OpenRouter OpenAI-compatible endpoints.
- Update BYOK runtime in `packages/rentl-llm/src/rentl_llm/openai_runtime.py` similarly.
- Forward typed OpenRouter provider settings (`require_parameters=true` baseline) to model settings.

## Task 7: Enforce Required Tool Usage Declaratively

- Extend agent profile schema (`packages/rentl-schemas/src/rentl_schemas/agents.py`) to support declarative required tools (e.g., `tools.required`).
- Validate `required ⊆ allowed` at schema level.
- Update agent TOML profiles in `packages/rentl-agents/agents/**/*.toml` to declare required tools where correctness depends on tool data.
- Wire required-tool declarations into `ProfileAgentConfig.required_tool_calls`.

## Task 8: Align Quality Harness and Production Execution

- Remove any quality-only behavior that differs from production runtime assumptions.
- Ensure quality harness (`tests/quality/agents/quality_harness.py`) and production both execute the same tool-only path.
- Add explicit checks that OpenRouter runs include provider constraints required for tool reliability.

## Task 9: Strengthen Errors and Telemetry for Tool Reliability

- Update runtime errors to be tool-mode specific (no output-mode recommendations that no longer exist).
- Include provider family, endpoint type, and tool compatibility context in failures (without leaking secrets).
- Add telemetry markers useful for postmortems: provider detected, tool calls observed, required tools satisfied.

## Task 10: Comprehensive Test Refactor

- Update and/or replace tests that currently assert `auto` or `prompted` behavior:
  - `tests/unit/rentl-agents/test_profile_agent_execute.py`
  - `tests/unit/rentl-agents/test_providers.py`
  - `tests/quality/agents/quality_harness.py`
  - `scripts/validate_agents.py` argument parsing tests (if present)
- Add schema tests in `tests/unit/schemas/test_config.py` and related suites for OpenRouter routing settings and required tool declarations.
- Keep integration coverage for OpenRouter runtime/provider selection in:
  - `tests/integration/byok/test_openrouter_runtime.py`
  - `tests/integration/byok/test_openai_runtime.py`

## Task 11: Verification - Run make all

Run `make all` and resolve all failures:

- format/lint (`ruff`)
- strict type checks (`ty`)
- unit tests
- integration tests
- quality tests

This task MUST pass before the spec is complete.

## Acceptance Checks

- Tool output is the only runtime output path; no operational dependency on `auto`, `prompted`, or `native`.
- OpenRouter requests for agent execution include provider constraints that require parameter support (including tool params).
- OpenRouter endpoints are executed through `OpenRouterModel` with typed settings propagation.
- Required tool calls are enforced declaratively and validated end-to-end.
- Quality and production exercise the same tool-only behavior.
- Errors and telemetry are actionable for diagnosing provider/tool-call failures.
- All checks in `make all` pass.
