spec_id: s0.1.31
issue: https://github.com/trevorWieland/rentl/issues/31
version: v0.1

# Plan: CLI Help/Doctor Commands

## Decision Record

Users need built-in diagnostics to troubleshoot setup issues, discover commands, and understand pipeline phases. The existing `validate-connection` command covers LLM connectivity but there's no unified diagnostic tool. This spec adds three commands (`help`, `doctor`, `explain`) following the thin adapter pattern — all logic in `rentl-core`, CLI layer only formats output.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit spec artifacts on issue branch

- [x] Task 2: Core Doctor Diagnostics Module
  - Create `packages/rentl-core/src/rentl_core/doctor.py`
  - Define `CheckResult` Pydantic model (name, status: pass/fail/warn, message, fix_suggestion)
  - Define `DoctorReport` Pydantic model (checks list, overall status)
  - Implement individual check functions: `check_python_version()`, `check_config_file()`, `check_config_valid()`, `check_workspace_dirs()`, `check_api_keys()`, `check_llm_connectivity()` (async)
  - Implement `run_doctor()` that runs all checks and returns `DoctorReport`
  - Unit tests for each check function (mock filesystem/env for isolation)
  - Acceptance: all checks return `CheckResult` with actionable fix suggestions; `run_doctor()` aggregates correctly
  - [x] Fix: Provide an actionable `fix_suggestion` for WARN status when runtime is missing in `run_doctor()` (currently `None` at `packages/rentl-core/src/rentl_core/doctor.py:438`; violates spec acceptance for warned checks) (audit round 1)
  - [x] Fix: Map LLM connectivity failure to connection-category exit code in `run_doctor()` instead of always returning `ExitCode.CONFIG_ERROR` for any failure (`packages/rentl-core/src/rentl_core/doctor.py:446`) (audit round 1)
  - [x] Fix: Include the workspace directory itself in `check_workspace_dirs()` fix command when workspace is missing (message lists workspace missing but suggestion omits it at `packages/rentl-core/src/rentl_core/doctor.py:226`) (audit round 1)
  - [x] Fix: Update `run_doctor()` exit-code aggregation so config-check failures take precedence over connection errors (currently returns `ExitCode.CONNECTION_ERROR` when `API Keys` fails and `LLM Connectivity` fails; see `packages/rentl-core/src/rentl_core/doctor.py:458` and repro in signposts) (audit round 2)
  - [x] Fix: Add regression test that asserts missing API key yields `ExitCode.CONFIG_ERROR` even when connectivity check also fails (extend `tests/unit/core/test_doctor.py` near `TestRunDoctor` around `tests/unit/core/test_doctor.py:511`) (audit round 2)

- [x] Task 3: Core Phase Explainer Module
  - Create `packages/rentl-core/src/rentl_core/explain.py`
  - Define `PhaseInfo` Pydantic model (name, description, inputs, outputs, prerequisites, config_options)
  - Build phase registry with info for all 7 phases sourced from `PhaseName` enum
  - Implement `get_phase_info(phase_name)` and `list_phases()`
  - Validate phase names against `PhaseName` enum
  - Unit tests for phase info retrieval and validation
  - Acceptance: all 7 phases have complete info; invalid names raise with valid phase list

- [x] Task 4: Core Help Content Module
  - Create `packages/rentl-core/src/rentl_core/help.py`
  - Define `CommandInfo` Pydantic model (name, brief, detailed_help, args, options, examples)
  - Build command registry from existing CLI commands
  - Implement `get_command_help(name)` and `list_commands()`
  - Unit tests for help content retrieval
  - Acceptance: all existing commands plus new commands are registered; invalid names handled
  - [x] Fix: Correct `run-pipeline` help metadata to match the real CLI flag (`--target-language` repeatable, not `--target-languages`) and update the example invocation (`packages/rentl-core/src/rentl_core/help.py:120`, `packages/rentl-core/src/rentl_core/help.py:124`, `services/rentl-cli/src/rentl_cli/main.py:163`, `services/rentl-cli/src/rentl_cli/main.py:504`) (audit round 1)
  - [x] Fix: Add regression test coverage that fails if `run-pipeline` help advertises flags/examples not accepted by the CLI signature (`packages/rentl-core/tests/unit/core/test_help.py:148`, `services/rentl-cli/src/rentl_cli/main.py:163`, `services/rentl-cli/src/rentl_cli/main.py:504`) (audit round 1)
  - [x] Fix: Align `export --column-order` help metadata with the real CLI signature (repeatable option, not comma-separated input) in `packages/rentl-core/src/rentl_core/help.py:95` to match `services/rentl-cli/src/rentl_cli/main.py:145` (audit round 2)
  - [x] Fix: Add regression test coverage asserting export help text/examples do not advertise comma-separated `--column-order` usage and stay aligned with the repeatable CLI option (`packages/rentl-core/tests/unit/core/test_help.py`, `services/rentl-cli/src/rentl_cli/main.py:145`) (audit round 2)

- [x] Task 5: CLI Commands — help, doctor, explain
  - Add `rentl help` command to CLI (thin adapter over core help module)
  - Add `rentl doctor` command to CLI (thin adapter over core doctor module, Rich-formatted table)
  - Add `rentl explain` command to CLI (thin adapter over core explain module, Rich-formatted output)
  - Pipe-safe output (detect TTY, degrade to plain text)
  - Exit code mapping from DoctorReport to ExitCode taxonomy
  - Integration tests for CLI invocation of all three commands
  - Acceptance: CLI commands work end-to-end; Rich formatting renders correctly; exit codes correct
  - [x] Fix: Add CLI tests that force `sys.stdout.isatty()` to `True` and assert Rich table/panel rendering paths for `help` and `explain` are exercised (`services/rentl-cli/src/rentl_cli/main.py:214`, `services/rentl-cli/src/rentl_cli/main.py:236`, `services/rentl-cli/src/rentl_cli/main.py:396`, `services/rentl-cli/src/rentl_cli/main.py:421`) (audit round 1)
  - [x] Fix: Add a CLI test that forces `sys.stdout.isatty()` to `True` and validates `doctor` Rich table + overall rendering path and non-success exit propagation (`services/rentl-cli/src/rentl_cli/main.py:308`, `services/rentl-cli/src/rentl_cli/main.py:334`, `services/rentl-cli/src/rentl_cli/main.py:374`) (audit round 1)
  - [x] Fix: Replace ineffective `sys.stdout.isatty` monkeypatching in TTY tests with a hook that actually affects CLI command execution under `CliRunner`; current patches at `tests/unit/cli/test_main.py:1756`, `tests/unit/cli/test_main.py:1774`, and `tests/unit/cli/test_main.py:1795` do not force the Rich branches in `services/rentl-cli/src/rentl_cli/main.py:214`, `services/rentl-cli/src/rentl_cli/main.py:236`, `services/rentl-cli/src/rentl_cli/main.py:308`, `services/rentl-cli/src/rentl_cli/main.py:396`, and `services/rentl-cli/src/rentl_cli/main.py:421` (audit round 2)
  - [x] Fix: Strengthen `test_doctor_command_tty_rendering` to assert non-success exit propagation explicitly for a controlled failing check set; it currently only checks output length at `tests/unit/cli/test_main.py:1816` and never verifies `services/rentl-cli/src/rentl_cli/main.py:374` behavior (audit round 2)

- [x] Task 6: Cross-command Polish and Edge Cases
  - `rentl doctor` outside project dir (no config) — graceful failure
  - `rentl explain badphase` — helpful error with valid phase list
  - `rentl help badcommand` — helpful error with valid command list
  - Verify Rich formatting works and degrades correctly when piped
  - Integration tests for edge cases
  - Acceptance: all edge cases handled gracefully with helpful error messages
  - [x] Fix: Add task-level implementation evidence for Task 6; commit `c6d57b7` changes only `plan.md` and provides no CLI/test diffs for these edge cases (audit round 1)
  - [x] Fix: Add or update edge-case integration coverage in `tests/integration/cli/test_doctor.py`, `tests/integration/cli/test_help.py`, and `tests/integration/cli/test_explain.py` for the exact Task 6 scenarios (audit round 1)
  - [x] Fix: Add explicit non-TTY (piped/plain-text) output assertions for `help`, `doctor`, and `explain` in `tests/unit/cli/test_main.py` and include them in the Task 6 implementation commit (audit round 1)
