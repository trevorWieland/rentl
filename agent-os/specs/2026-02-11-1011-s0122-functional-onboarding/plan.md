spec_id: s0.1.22
issue: https://github.com/trevorWieland/rentl/issues/23
version: v0.1

# Plan: Functional Onboarding

## Decision Record

The individual onboarding commands (`init`, `doctor`, `help`, `explain`) are complete and tested, but the end-to-end flow has integration gaps. This spec closes those gaps to meet the v0.1 success criterion: "A new user can run `rentl init` -> full pipeline -> export without manual edits." The work is scoped to functional fixes and a basic README — exhaustive docs are deferred to s0.1.30.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on issue branch and push

- [x] Task 2: Fix doctor `.env` loading
  - Add `_load_dotenv(config_path)` call to the `doctor()` command in `services/rentl-cli/src/rentl_cli/main.py` before running checks
  - Update doctor fix suggestions in `packages/rentl-core/src/rentl_core/doctor.py` to reference `.env` loading and provide copy-pasteable fix commands
  - Add unit tests for dotenv loading in doctor context (`tests/unit/core/test_doctor.py`)
  - Update integration test (`tests/integration/cli/test_doctor.py`)
  - Acceptance: `rentl doctor` passes API key check when key is only in `.env` file
  - [x] Fix: Add unit coverage in `tests/unit/core/test_doctor.py` for dotenv loading behavior in doctor context (at minimum: `.env` load path and `.env.local` handling), since Task 2 commit `4258ec3` did not modify this file (audit round 1)
  - [x] Fix: Add/move dotenv-loading tests into `tests/unit/core/test_doctor.py` (doctor-context coverage for config-dir `.env` path and `.env.local` handling); current additions were made in `tests/unit/cli/test_main.py` instead (audit round 2)
  - [x] Fix: Correct the inaccurate precedence claim in `tests/unit/core/test_doctor.py:811` ("`.env.local` takes precedence") to match actual behavior (`.env` currently wins because both loads use `override=False` in `services/rentl-cli/src/rentl_cli/main.py:2129-2132`; verified in `tests/unit/cli/test_main.py:2350`) (audit round 3; see signposts.md Signpost 1)
  - [x] Fix: Strengthen dotenv doctor-context coverage in `tests/unit/core/test_doctor.py:787-819` to assert real `.env`/`.env.local` load behavior rather than only setting environment variables via `monkeypatch.setenv(...)`, per `testing/mandatory-coverage` (audit round 3)

- [x] Task 3: Add provider presets to `rentl init`
  - Add provider preset data structure with at least 3 presets: OpenRouter, OpenAI, Local/Ollama
  - Each preset pre-fills: base_url, api_key_env, default model_id
  - Replace raw URL prompts with provider selection menu in CLI init command
  - Add "Custom" option that prompts for all fields manually
  - Add URL format validation (reject non-URL strings like "not-a-url")
  - Update unit tests (`tests/unit/core/test_init.py`)
  - Update integration tests (`tests/integration/cli/test_init.py`)
  - Acceptance: running `rentl init` shows provider choices; selecting one pre-fills URL/key/model; custom entry validates URL format
  - [x] Fix: Restrict provider selection to valid menu choices in `services/rentl-cli/src/rentl_cli/main.py:587-596`; currently out-of-range numeric input (e.g., `999`) falls through to the Custom branch instead of returning a validation error (audit round 1; see signposts.md Signpost 3)
  - [x] Fix: Add CLI init coverage in `tests/unit/cli/test_main.py` for provider menu behavior introduced at `services/rentl-cli/src/rentl_cli/main.py:570-628` (preset selection, out-of-range rejection, and custom URL validation loop) per `testing/mandatory-coverage` (audit round 1)

- [x] Task 4: Add post-run next steps to pipeline summary
  - After `rentl run-pipeline` completes, append next steps to the summary panel in `services/rentl-cli/src/rentl_cli/main.py` (`_render_run_execution_summary`)
  - Show: `rentl export` command and the configured output directory path
  - If export phase was already included in the run, show the output file paths instead
  - Add unit test for summary rendering with next steps
  - Acceptance: pipeline summary includes actionable next steps referencing export
  - [x] Fix: In the export-completed branch of `_render_run_execution_summary`, render concrete exported file paths instead of the output directory (`services/rentl-cli/src/rentl_cli/main.py:2538-2543` currently prints `config.project.paths.output_dir` under the label `Output files:`) (audit round 1; see signposts.md Signpost 4)
  - [x] Fix: Strengthen summary tests to assert actual exported file-path rendering for export-completed runs (e.g., derive from `RunState.artifacts`) instead of only checking label presence (`tests/unit/cli/test_main.py:1147-1233`), per `testing/mandatory-coverage` (audit round 1; see signposts.md Signpost 4)

- [ ] Task 5: Add project README.md
  - Write root-level `README.md` with:
    - What rentl is (brief pitch from mission.md)
    - Installation instructions (uv/uvx)
    - Quickstart flow: `init -> doctor -> run-pipeline -> export`
    - CLI command reference table
    - Links to license
  - Keep it concise — exhaustive docs are s0.1.30
  - Acceptance: README exists, covers all listed sections, is accurate

- [ ] Task 6: End-to-end onboarding integration test
  - BDD integration test in `tests/integration/cli/test_onboarding_e2e.py`
  - Exercises full flow: `init -> doctor -> run-pipeline -> export` with mocked LLM
  - Verifies: generated config is valid, doctor passes, pipeline completes, export produces output files
  - No manual edits between steps
  - Acceptance: test passes in `make all`
