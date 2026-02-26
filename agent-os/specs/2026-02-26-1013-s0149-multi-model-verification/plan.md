spec_id: s0.1.49
issue: https://github.com/trevorWieland/rentl/issues/144
version: v0.1

# Plan: Multi-Model Verification & Compatibility

## Decision Record
rentl's v0.1 promise includes BYOK model support, but "support" is meaningless without verification. This spec creates a systematic way to verify that specific models work through the full pipeline, with both a CLI tool for ad-hoc checks and a test suite for regression safety. The registry is data-driven so expanding model coverage is a config edit, not a code change.

## Tasks
- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit and push on issue branch
- [x] Task 2: Create verified-models registry schema and file
  - Define Pydantic schema for registry entries: model_id, endpoint_type (local/openrouter), endpoint_ref, config overrides (timeout, temperature, etc.), load_endpoint for local models
  - Create TOML registry file with all 9 models (4 local + 5 OpenRouter)
  - Add unit tests for schema validation and TOML loading
  - Files: `packages/rentl-schemas/src/rentl_schemas/compatibility.py`, registry TOML location, `tests/unit/schemas/test_compatibility.py`
  - Acceptance: schema loads and validates all 9 entries; invalid entries rejected
  - [x] Fix: Handle non-string/null `endpoint_type` inputs in validator without raising raw `AttributeError`; reject with a Pydantic `ValidationError` path instead (`packages/rentl-schemas/src/rentl_schemas/compatibility.py:56-59`) (audit round 1)
  - [x] Fix: Add unit coverage for `endpoint_type=None` (and/or non-string) to confirm invalid entries are rejected via validation errors (`tests/unit/schemas/test_compatibility.py`) (audit round 1)
  - [x] Fix: Remove `object` annotation from `_coerce_endpoint_type` validator signature and use explicit non-`Any` typing to satisfy `strict-typing-enforcement` (`packages/rentl-schemas/src/rentl_schemas/compatibility.py:58`) (audit round 2)
- [x] Task 3: Build shared verification runner with model loading
  - Core logic that takes a registry entry, resolves the endpoint, and runs a mini 5-phase pipeline on golden input data
  - For local models: call LM Studio load API (`http://192.168.1.23:1234/api/v1/models/load`) to switch active model before verification
  - Return structured pass/fail results per phase with error details
  - Sequential execution for local models (one at a time); parallel-safe for OpenRouter
  - Files: `packages/rentl-core/src/rentl_core/compatibility/` (runner, loader, types)
  - Tests: unit tests with mocked LLM calls + mocked load API
  - Acceptance: runner produces correct results for mock scenarios; load API integration works
  - [x] Fix: Preserve explicit zero-valued config overrides (`temperature=0.0`, `top_p=0.0`) by using `is not None` checks instead of truthy `or` fallbacks in `verify_model` (`packages/rentl-core/src/rentl_core/compatibility/runner.py:261-264`) (audit round 1)
  - [x] Fix: Replace `object` type annotations in the `_side_effect` test helper with explicit concrete types to satisfy `strict-typing-enforcement` (`tests/unit/core/compatibility/test_runner.py:126-127`) (audit round 1)
- [x] Task 4: Add `rentl verify-models` CLI command
  - Thin CLI adapter that reads the registry, invokes the shared runner, displays results
  - Supports `--endpoint` filter (local/openrouter/all) and `--model` filter
  - Reports per-model, per-phase pass/fail with actionable error messages
  - Files: `packages/rentl-cli/src/rentl_cli/commands/verify_models.py`
  - Tests: unit tests for CLI argument parsing, output formatting, wiring to shared runner
  - Acceptance: `rentl verify-models --help` works; output is clear and actionable
  - [x] Fix: Wrap `asyncio.run(verify_registry(...))` in CLI error handling so unexpected verifier/runtime exceptions return actionable CLI output instead of propagating uncaught (`services/rentl-cli/src/rentl/main.py:3885-3892`) (audit round 1, see signposts.md: Task 4 unresolved verifier exception handling)
  - [x] Fix: Add unit tests for output formatting paths (TTY rich table + non-TTY JSON emission) to satisfy Task 4 test requirements (`tests/unit/cli/test_verify_models.py`) (audit round 1)
- [x] Task 5: Add pytest compatibility test suite
  - Quality-tier tests parameterized from the verified-models registry
  - BDD-style (Given/When/Then)
  - Loads local models via LM Studio API before each test — no skipping
  - Uses the same shared runner from Task 3
  - Files: `tests/quality/compatibility/test_model_compatibility.py`, `tests/quality/compatibility/conftest.py`
  - Acceptance: `make quality` runs all compatibility tests; zero skips
  - [x] Fix: Replace the current `pytest_generate_tests` approach with a real `model_entry` fixture parametrization that pytest-bdd can resolve, so the scenario no longer errors with `fixture 'model_entry' not found` (`tests/quality/compatibility/test_model_compatibility.py:43-50`, `tests/quality/compatibility/test_model_compatibility.py:76-78`) (audit round 1)
  - [x] Fix: Verify collection produces one compatibility test instance per registry model (9 expected from the bundled registry), not a single unparameterized scenario (`LM_STUDIO_API_KEY=dummy RENTL_OPENROUTER_API_KEY=dummy pytest -q tests/quality/compatibility/test_model_compatibility.py --collect-only` currently reports `collected 1 item`) (audit round 1)
- [ ] Task 6: Verify all target models pass and fix provider issues
  - Run CLI and test suite against all 9 models (4 local, 5 OpenRouter)
  - Fix any structured output or tool calling issues in provider handling — generically, no model-specific branches
  - Grep source code to confirm no hardcoded model name strings outside registry/fixtures
  - Acceptance: all 9 models pass; grep returns zero model-name hits in source
