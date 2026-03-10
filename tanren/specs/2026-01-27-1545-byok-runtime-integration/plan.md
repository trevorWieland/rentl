# BYOK Runtime Integration Plan

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-01-27-1545-byok-runtime-integration/` with:

- **plan.md** - This full plan
- **shape.md** - Shaping notes (scope, decisions, context)
- **standards.md** - Applicable standards (full text)
- **references.md** - Pointers to studied code
- **visuals/** - Any mockups or screenshots provided

## Task 2: Define core runtime interfaces and config wiring

- Add core protocol(s) for LLM runtime access and typed request/response schemas.
- Add config resolver that maps `RunConfig` + phase/model to runtime settings:
  - Resolve endpoint by precedence (agent -> phase -> default).
  - Support legacy `endpoint` and multi-endpoint `endpoints`.
  - Pull `model_id`, `timeout_s`, and `RetryConfig` into runtime settings.
- Keep CLI thin; business logic lives in core.

## Task 3: Implement OpenAI-compatible BYOK runtime adapter (pydantic-ai)

- Implement an infrastructure adapter that satisfies the core protocol.
- Configure `base_url`, API key, timeout, and retries from config.
- Ensure async-first API and strict typing.

## Task 4: Add CLI validate-connection command

- Add `validate-connection` command in CLI to run connectivity checks.
- Resolve all configured endpoints and the models that use them.
- Ping each model service using the core runtime adapter.
- Use config wiring for endpoint URL, API key env var, and model ID.
- Return `{data, error, meta}` envelope with per-endpoint results.

## Task 5: Tests (unit + integration)

- Unit tests for endpoint/model resolution and runtime settings mapping.
- Integration tests for CLI `validate-connection` with mocked LLM adapter.
- Follow three-tier test structure and timing rules.

## Task 6: Manual validation (local BYOK server)

- Use a config that sets:
  - `base_url = "http://172.17.32.1:1234"`
  - `model_id = "openai/gpt-oss-20b"`
  - `api_key_env` pointing to an env var set to `test-key`
- Run `validate-connection` to verify hello-world connectivity.
- Do not hard-code IP, key, or model anywhere in code.

## Task 7: Verification - Run make all

Run `make all` to ensure all code passes quality checks:

- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests

This task must pass before the spec is considered complete.
