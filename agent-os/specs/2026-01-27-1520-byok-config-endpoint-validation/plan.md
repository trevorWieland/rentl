# BYOK Config & Endpoint Validation Plan

## Goal
- Validate BYOK endpoint configuration without network preflight while supporting any OpenAI-compatible URL.
- Add multi-endpoint config with explicit endpoint resolution precedence (agent → phase → default).
- Keep legacy single-endpoint configs working without changes.
- Ensure CLI fails fast on missing API keys for endpoints in use.
- Unblock v0.1 BYOK runtime integration and future per-agent customization.

## Execution Note
- Execute Task 1 now, then continue with implementation tasks.

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals.

## Task 2: Expand endpoint config schema + validators
- Update `ModelEndpointConfig` descriptions to clarify label usage and validate `base_url` as http/https with a host; allow paths like `/v1` or `/api/v1`.
- Add `EndpointSetConfig` (default endpoint + list of endpoints) with uniqueness + default-exists validation.
- Add optional `endpoint_ref` to `ModelSettings` for per-phase and future per-agent selection.
- Update `RunConfig` validation to allow either legacy `endpoint` or new `endpoints` (mutually exclusive) and to validate endpoint refs.
- Add a resolver helper (schema-level) that documents endpoint selection precedence: agent → phase → default.

## Task 3: CLI endpoint validation updates
- Update `_ensure_api_key` in `services/rentl-cli/src/rentl_cli/main.py` to resolve endpoints used by LLM phases (phase override → default) and verify each `api_key_env` is present.
- Improve error messages for invalid base URLs or missing keys (hint to include `http://` for local endpoints).

## Task 4: Tests
- Add unit tests in `tests/unit/schemas/test_config.py` for base_url validation, endpoint uniqueness/default, endpoint_ref validation, and legacy vs multi-endpoint configs.
- Update/add CLI tests in `tests/unit/cli/test_main.py` to cover multi-endpoint key checks and keep legacy config passing.

## Task 5: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass.
- Fix failures and re-run until green.

## References Studied
- `packages/rentl-schemas/src/rentl_schemas/config.py`
- `packages/rentl-schemas/src/rentl_schemas/validation.py`
- `services/rentl-cli/src/rentl_cli/main.py`
- `tests/unit/cli/test_main.py`
- `tests/unit/schemas/test_config.py`

## Standards Applied
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- architecture/thin-adapter-pattern
- architecture/api-response-format
- ux/trust-through-transparency
- ux/frictionless-by-default
- ux/speed-with-guardrails
- testing/make-all-gate

## Product Alignment
- v0.1 requires BYOK OpenAI-compatible endpoints with strict schema validation and CLI-first workflows.
- v0.1 BYOK runtime integration depends on validated endpoint selection and key checks.
- v0.2+ agent roster and multi-agent specs rely on per-agent/phase endpoint resolution.
