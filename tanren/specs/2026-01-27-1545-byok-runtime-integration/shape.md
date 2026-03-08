# BYOK Runtime Integration - Shaping Notes

## Scope

- Implement OpenAI-compatible runtime client using pydantic-ai with retries/backoff.
- Add core protocol interfaces and config resolution wiring for runtime settings.
- Add CLI `validate-connection` command that pings every configured model service.
- Validation must use configured base_url, api key env var, and model_id (no hard-coded values).
- Provide a manual validation path using local server config.

## Decisions

- CLI stays a thin adapter; runtime resolution and connection logic live in core.
- Validate connectivity by iterating all resolved endpoints/models rather than a single model.
- The validation command name is `validate-connection` (future checks can be added here).
- No network preflight during config validation (still handled at runtime).

## Context

- **Visuals:** None
- **References:**
  - `agent-os/specs/2026-01-27-1520-byok-config-endpoint-validation/shape.md`
  - `packages/rentl-schemas/src/rentl_schemas/config.py`
  - `packages/rentl-schemas/src/rentl_schemas/validation.py`
  - `services/rentl-cli/src/rentl_cli/main.py`
  - `tests/unit/schemas/test_config.py`
  - `tests/unit/cli/test_main.py`
- **Product alignment:** v0.1 BYOK OpenAI-compatible endpoint support with strict schemas and CLI-first workflows.

## Standards Applied

- testing/make-all-gate - verification required before completion
- python/async-first-design - async runtime and IO
- python/modern-python-314 - modern language features
- python/strict-typing-enforcement - explicit types and Field usage
- architecture/thin-adapter-pattern - CLI remains a thin adapter
- architecture/adapter-interface-protocol - runtime access via protocol
- ux/trust-through-transparency - clear connectivity results and errors
- ux/frictionless-by-default - easy validation flow
- testing/three-tier-test-structure - tests in unit/integration/quality
- testing/no-mocks-for-quality-tests - mock LLMs in integration, real in quality
