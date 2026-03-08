spec_id: s0.1.28
issue: https://github.com/trevorWieland/rentl/issues/112
version: v0.1

# Shape: OpenRouter Full Support

## Summary
Enforce a tool-only agent runtime across providers, with OpenRouter configured to route only to endpoints that support required tool parameters. Reliability must come from runtime invariants and typed configuration, not model-specific heuristics.

## Problem
OpenRouter runs are intermittently unreliable because runtime behavior is split across multiple output paths and provider routing may land on endpoints that do not fully honor tool requirements. Quality checks and production have also exercised different behavior in places, making failures hard to predict.

## Goals
- Tool-only execution path for phase agents across OpenRouter, OpenAI-compatible endpoints, and local endpoints.
- OpenRouter requests constrained with provider settings that require parameter support (`require_parameters=true`) so incompatible providers are excluded.
- OpenRouter execution uses `OpenRouterModel` with typed settings propagation for parity and reliability.
- Provider switching remains config-only, without prompt/profile rewrites.
- Errors and telemetry are explicit and useful for diagnosing tool-call failures.

## Non-Goals
- Model-specific hardcoding or per-model runtime exceptions.
- Supporting mixed output-mode strategies (`auto`, `prompted`, `native`) for phase agents.
- Reworking unrelated pipeline logic or non-LLM phases.

## Constraints
- Must preserve async-first design, strict typing, and pydantic-only schemas.
- Must comply with `@agent-os/standards/python/strict-typing-enforcement.md` (no `Any`/`object` for internal schemas).

## Scope
- Remove runtime dependence on `auto`/`prompted`/`native` for phase-agent structured output.
- Unify provider detection and tool capability enforcement across agent runtime and BYOK runtime.
- Add typed OpenRouter provider-routing config in run config and propagate to runtime model settings.
- Introduce declarative required-tool enforcement at profile/schema level and wire it end-to-end.
- Align quality harness behavior with production tool-only runtime behavior.
- Expand tests to prove tool-only parity and OpenRouter routing constraints.

## Success Criteria
- Tool output is the only operational path for phase agents.
- OpenRouter agent requests include provider constraints that require parameter support for tools.
- OpenRouter endpoints are executed via `OpenRouterModel` with typed settings.
- Required tool calls are enforced declaratively and validated in runtime behavior.
- Quality and production follow the same execution assumptions.
- `make all` passes with updated unit/integration/quality coverage.

## Risks
- OpenRouter provider slugs and support capabilities can change over time; config and tests must tolerate provider evolution.
- Over-constraining provider routing may reduce fallback options and increase hard failures when provider capacity is low.
- Migration from mixed-mode assumptions may require broad test and fixture updates.

## Open Questions
- Do we want default OpenRouter provider ordering in config templates, or keep ordering fully user-defined?
- Should connection validation include a preflight capability check for tool-required routes before full phase execution?
