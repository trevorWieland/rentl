spec_id: s0.1.29
issue: https://github.com/trevorWieland/rentl/issues/29
version: v0.1

# Plan: Project Bootstrap Command

## Decision Record

Users currently must manually copy and edit config files to start a project, violating the "frictionless by default" UX standard. This spec adds `rentl init` as an interactive bootstrap command that scaffolds a ready-to-run project. The design uses Pydantic models for the interview answers and generation results, keeping the core logic in `rentl-core` and the CLI as a thin adapter. The `[agents]` config section is made optional so generated configs don't need to reference package-internal paths.

## Tasks

- [x] Task 1: Save Spec Documentation
- [ ] Task 2: Make `[agents]` config section optional
  - Update `RunConfig` in `rentl-schemas/src/rentl_schemas/config.py` to make `agents` field optional (default `None`)
  - Update CLI `_resolve_agent_paths()` in `services/rentl-cli/src/rentl_cli/main.py` to skip resolution when agents is `None`
  - Update `build_agent_pools()` in `packages/rentl-agents/src/rentl_agents/wiring.py` to use `get_default_agents_dir()`/`get_default_prompts_dir()` when agents config is `None`
  - Update existing tests that assume agents config is always present
  - Test: config without `[agents]` section validates and pipeline resolves to package defaults
- [ ] Task 3: Define init interview schema and core logic
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
- [ ] Task 4: Add `rentl init` CLI command
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
- [ ] Task 5: Integration test — init produces runnable project
  - Integration test in `services/rentl-cli/tests/integration/` using BDD format
  - Given: empty temp directory
  - When: `generate_project()` is called with default answers
  - Then: generated `rentl.toml` passes `validate_run_config()`
  - And: all expected files exist (`rentl.toml`, `.env`, `input/`, `out/`, `logs/`)
  - And: seed data file is valid JSONL with expected `SourceLine` structure
  - And: config round-trips through TOML parse → validate → resolve without errors
