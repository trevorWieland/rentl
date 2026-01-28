# BYOK Config & Endpoint Validation — Shaping Notes

## Scope
- Add static validation for BYOK endpoints (no network preflight) and accept any OpenAI-compatible base URL.
- Support multiple endpoints with a clear endpoint resolution precedence (agent → phase → default).
- Keep legacy single-endpoint configuration working without changes.
- Fail fast on missing API key env vars for endpoints used by LLM phases.

## Decisions
- Validation is static-only in this spec; network preflight is deferred to runtime integration.
- `provider_name` remains a user-defined label and does not drive provider-specific logic.
- Base URLs must be http/https with a host; paths like `/v1` or `/api/v1` are allowed.
- Endpoint selection precedence is explicit (agent → phase → default) to support future per-agent customization.
- No provider allowlist; any OpenAI-compatible endpoint is valid (OpenAI, OpenRouter, Ollama, LM Studio, etc.).
- Legacy `endpoint` config is supported alongside new multi-endpoint config (mutually exclusive fields).

## Context
- **Visuals:** None
- **References:**
  - `packages/rentl-schemas/src/rentl_schemas/config.py`
  - `packages/rentl-schemas/src/rentl_schemas/validation.py`
  - `services/rentl-cli/src/rentl_cli/main.py`
  - `tests/unit/cli/test_main.py`
  - `tests/unit/schemas/test_config.py`
- **Product alignment:** v0.1 requires BYOK OpenAI-compatible endpoints, strict schemas, and CLI-first workflows; forward compatibility with agent/phase-specific model routing is required.

## Standards Applied
- testing/make-all-gate — verification required before completion.
- python/pydantic-only-schemas — new config schemas must be Pydantic.
- python/strict-typing-enforcement — no `Any`, all fields use `Field` with descriptions and validators.
- architecture/thin-adapter-pattern — CLI remains a thin adapter over schema/core validation.
- architecture/api-response-format — CLI error output stays in `{data, error, meta}` envelope.
- ux/trust-through-transparency — validation errors must be clear and actionable.
- ux/frictionless-by-default — errors include hints (e.g., add `http://` for localhost).
- ux/speed-with-guardrails — validate early without blocking runtime workflows.
