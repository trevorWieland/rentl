spec_id: s0.1.29
issue: https://github.com/trevorWieland/rentl/issues/29
version: v0.1

# Plan: Project Bootstrap Command

## Decision Record

Users currently must manually copy and edit config files to start a project, violating the "frictionless by default" UX standard. This spec adds `rentl init` as an interactive bootstrap command that scaffolds a ready-to-run project. The design uses Pydantic models for the interview answers and generation results, keeping the core logic in `rentl-core` and the CLI as a thin adapter. The `[agents]` config section is made optional so generated configs don't need to reference package-internal paths.

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Make `[agents]` config section optional
  - Update `RunConfig` in `rentl-schemas/src/rentl_schemas/config.py` to make `agents` field optional (default `None`)
  - Update CLI `_resolve_agent_paths()` in `services/rentl-cli/src/rentl_cli/main.py` to skip resolution when agents is `None`
  - Update `build_agent_pools()` in `packages/rentl-agents/src/rentl_agents/wiring.py` to use `get_default_agents_dir()`/`get_default_prompts_dir()` when agents config is `None`
  - Update existing tests that assume agents config is always present
  - Test: config without `[agents]` section validates and pipeline resolves to package defaults
  - [x] Fix: Add a unit test that executes `build_agent_pools(config=...)` with `RunConfig.agents=None` and asserts default package directories are used through successful pool construction (`packages/rentl-agents/src/rentl_agents/wiring.py:1124`) (audit round 1)
  - [x] Fix: Strengthen the CLI regression test to verify pipeline/default-agent resolution instead of only config parsing; current assertion stops at `_load_resolved_config()` (`tests/unit/cli/test_main.py:367`) (audit round 1)
- [x] Task 3: Define init interview schema and core logic
  - Create `packages/rentl-core/src/rentl_core/init.py` with:
    - `InitAnswers` Pydantic model (project_name, game_name, source_language, target_languages, provider_name, base_url, api_key_env, model_id, input_format, include_seed_data)
    - `InitResult` Pydantic model (created_files: list of paths, next_steps: list of instruction strings)
    - `generate_project(answers: InitAnswers, target_dir: Path) -> InitResult` function
  - Config generation produces valid TOML matching `RunConfig` schema (without `[agents]` section)
  - `.env` generation with placeholder for the chosen API key env var
  - Directory creation: `input/`, `out/`, `logs/`
  - Seed data: 3 sample JSONL lines (1 scene) with placeholder game dialogue when `include_seed_data=True`
  - Export `InitAnswers`, `InitResult`, `generate_project` from `rentl_core.__init__`
  - Unit tests: `generate_project()` with default answers produces valid config and expected file structure
  - [x] Fix: Restrict `InitAnswers.input_format` to `RunConfig`-compatible formats so every accepted answer can produce a validating config (current `str` type accepts unsupported `tsv`) (`packages/rentl-core/src/rentl_core/init.py:43`, `packages/rentl-schemas/src/rentl_schemas/primitives.py:84`) (audit round 1)
  - [x] Fix: Align seed-data generation/tests with supported formats and add a regression test that unsupported formats are rejected before writing invalid TOML (`packages/rentl-core/src/rentl_core/init.py:226`, `tests/unit/core/test_init.py:164`) (audit round 1)
- [x] Task 4: Add `rentl init` CLI command
  - Add `init` command to `services/rentl-cli/src/rentl_cli/main.py`
  - Use Typer `typer.prompt()` for each interview question with sensible defaults:
    - project_name: derived from current directory name
    - game_name: derived from project_name
    - source_language: `ja`
    - target_languages: `en` (comma-separated input parsed to list)
    - provider_name: `openrouter`
    - base_url: `https://openrouter.ai/api/v1`
    - api_key_env: `OPENROUTER_API_KEY`
    - model_id: `openai/gpt-4.1`
    - input_format: `jsonl`
    - include_seed_data: `True`
  - Check for existing `rentl.toml` — if found, use `typer.confirm()` to ask before overwriting
  - Call `generate_project()` from rentl-core
  - Print Rich-formatted summary panel with created files and next-step instructions
  - Follow existing command patterns (ApiResponse envelope, exit codes)
  - Unit tests: CLI command happy path, overwrite confirmation flow
  - [x] Fix: Preserve `typer.Exit` passthrough in `init()` so overwrite cancellation exits cleanly instead of entering `_error_from_exception()` (`services/rentl-cli/src/rentl_cli/main.py:211`, `services/rentl-cli/src/rentl_cli/main.py:290`) (audit round 1)
  - [x] Fix: Add CLI unit tests for `rentl init` happy path and overwrite confirmation/cancel flow (including cancellation exit code assertions) (`tests/unit/cli/test_main.py`) (audit round 1)
  - [x] Fix: Sanitize comma-separated target language input in CLI init to drop empty entries and fail fast on blank results before calling `generate_project()`; current split logic accepts trailing commas and can generate invalid config (`services/rentl-cli/src/rentl_cli/main.py:227`) (audit round 2)
  - [x] Fix: Add CLI regression coverage for `target_languages` parsing (for example `en,` and `en, fr`) and assert generated `rentl.toml` passes `validate_run_config()` for accepted inputs (`tests/unit/cli/test_main.py`) (audit round 2)
- [x] Task 5: Integration test — init produces runnable project
  - Integration test in `services/rentl-cli/tests/integration/` using BDD format
  - Given: empty temp directory
  - When: `generate_project()` is called with default answers
  - Then: generated `rentl.toml` passes `validate_run_config()`
  - And: all expected files exist (`rentl.toml`, `.env`, `input/`, `out/`, `logs/`)
  - And: seed data file is valid JSONL with expected `SourceLine` structure
  - And: config round-trips through TOML parse → validate → resolve without errors
- [x] Task 6: Fix generated config to use correct default agent names
  - Update `_generate_toml()` in `packages/rentl-core/src/rentl_core/init.py` lines 163, 167, 171, 175, 179
  - Replace generic phase-name agents with actual default agent names:
    - context: `["scene_summarizer"]` not `["context"]`
    - pretranslation: `["idiom_labeler"]` not `["pretranslation"]`
    - translate: `["direct_translator"]` not `["translate"]`
    - qa: `["style_guide_critic"]` not `["qa"]`
    - edit: `["basic_editor"]` not `["edit"]`
  - Reference: `rentl.toml.example` for correct agent names
  - Update unit tests in `tests/unit/core/test_init.py` to verify correct agent names in generated TOML
  - Extend integration test in `tests/integration/cli/test_init.py` to verify pipeline can actually build agent pools from generated config (not just schema validation)
  - [x] Fix: Make the new agent-pool integration assertion deterministic by setting a test API key env var before calling `build_agent_pools()`; current step fails in clean environments with `ValueError: Missing API key environment variable: OPENROUTER_API_KEY` (`tests/integration/cli/test_init.py:53`, `tests/integration/cli/test_init.py:210`) (audit round 1)
  - [x] Fix: Add regression coverage that the env var setup/teardown is scoped to the test so `test_init_produces_runnable_project` passes without relying on external shell environment (`tests/integration/cli/test_init.py:190`) (audit round 1)
  - [x] Fix: Remove the ambient-environment precondition in `test_env_var_scoping_regression`; the current `assert "OPENROUTER_API_KEY" not in os.environ` fails when the variable is already set in the shell, making the regression test non-deterministic (`tests/integration/cli/test_init.py:246`) (audit round 2)
  - [x] Fix: Assert real setup/teardown scoping for the API key env var using an isolated patch scope (for example `monkeypatch.context()`), so the test proves temporary override + restoration regardless of pre-existing environment state (`tests/integration/cli/test_init.py:272`) (audit round 2)
- [x] Task 7: Add missing ingest and export phases to generated pipeline config
  - Update `_generate_toml()` in `packages/rentl-core/src/rentl_core/init.py` line 161 to add `ingest` phase before `context` phase
  - Update `_generate_toml()` in `packages/rentl-core/src/rentl_core/init.py` line 179 to add `export` phase after `edit` phase
  - Reference: `rentl.toml.example` lines 38-39 for ingest phase, lines 61-62 for export phase
  - Update unit tests in `tests/unit/core/test_init.py` to verify generated TOML includes ingest and export phases
  - Update integration test in `tests/integration/cli/test_init.py` to verify complete pipeline can execute (not just build agent pools)
  - [x] Fix: Replace the integration assertion that only calls `build_agent_pools()` with an end-to-end execution assertion that actually runs the generated pipeline through ingest and export using deterministic test doubles (`tests/integration/cli/test_init.py:192`, `tests/integration/features/cli/init.feature:14`) (audit round 1)
  - [x] Fix: Add explicit assertions that export artifacts are produced by the execution path so the test proves runnable-project behavior instead of configuration-only validity (`tests/integration/cli/test_init.py:192`) (audit round 1)
  - [x] Fix: Align generated seed-input behavior with configured `project.paths.input_path` so default `include_seed_data=True` projects run end-to-end without manual file moves; current run fails with `No such file or directory: .../input/Test Game.jsonl` because generation writes `input/seed.jsonl` (`packages/rentl-core/src/rentl_core/init.py:99`, `packages/rentl-core/src/rentl_core/init.py:105`, `packages/rentl-core/src/rentl_core/init.py:133`) (audit round 2)
  - [x] Fix: Add/adjust regression coverage to assert seeded input file path matches the generated config input path and that `test_init_produces_runnable_project` succeeds via `run-pipeline` with no extra fixture-side file rewriting (`tests/integration/cli/test_init.py:233`, `tests/unit/core/test_init.py`) (audit round 2)
  - [x] Fix: Make the Task 7 end-to-end test double return schema-valid outputs for default agents (or stub the agent execution boundary) so `run-pipeline` can complete deterministically; current `FakeLlmRuntime` returns `output_text="ok"` and the scenario fails with `Agent scene_summarizer execution failed after 4 attempts` (`tests/integration/conftest.py:30`, `tests/integration/cli/test_init.py:241`) (audit round 3)
  - [x] Fix: Add a regression assertion in the Task 7 integration path that the mocked runtime output is accepted by `scene_summarizer` and downstream phases, proving export artifacts are produced under the same deterministic stub used in the test (`tests/integration/cli/test_init.py:231`, `tests/integration/cli/test_init.py:267`) (audit round 3)
  - [x] Fix: Restore true end-to-end execution coverage in the BDD step by invoking `rentl run-pipeline` (or equivalent orchestrator execution path) and asserting successful completion; the current step labeled "execute end-to-end" only validates config + `build_agent_pools()` (`tests/integration/cli/test_init.py:194`, `tests/integration/cli/test_init.py:233`) (audit round 4)
  - [x] Fix: Add explicit assertions for generated export artifacts after execution (for example `out/{target_language}/output.{format}`); current Task 7 step checks only directory existence and never verifies export outputs (`tests/integration/cli/test_init.py:246`, `tests/integration/cli/test_init.py:259`) (audit round 4)
  - [x] Fix: Patch the deterministic test double at the execution boundary actually used by `run-pipeline` (agent execution via `build_agent_pools()`), because patching `cli_main._build_llm_runtime` does not affect this path; currently `test_init_produces_runnable_project` fails with `exit code 99` / `Agent scene_summarizer execution failed after 4 attempts` (`tests/integration/cli/test_init.py:264`, `tests/integration/conftest.py:149`, `services/rentl-cli/src/rentl_cli/main.py:1404`) (audit round 5)
  - [x] Fix: Add a regression assertion that the patched execution boundary was invoked during `run-pipeline` and keep the export-artifact assertions (`out/{lang}/output.{format}`) gated on a successful `exit_code == 0` run (`tests/integration/cli/test_init.py:257`, `tests/integration/cli/test_init.py:281`) (audit round 5)
