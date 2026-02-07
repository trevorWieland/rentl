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

- [ ] Task 2: Core Doctor Diagnostics Module
  - Create `packages/rentl-core/src/rentl_core/doctor.py`
  - Define `CheckResult` Pydantic model (name, status: pass/fail/warn, message, fix_suggestion)
  - Define `DoctorReport` Pydantic model (checks list, overall status)
  - Implement individual check functions: `check_python_version()`, `check_config_file()`, `check_config_valid()`, `check_workspace_dirs()`, `check_api_keys()`, `check_llm_connectivity()` (async)
  - Implement `run_doctor()` that runs all checks and returns `DoctorReport`
  - Unit tests for each check function (mock filesystem/env for isolation)
  - Acceptance: all checks return `CheckResult` with actionable fix suggestions; `run_doctor()` aggregates correctly
  - [ ] Fix: Provide an actionable `fix_suggestion` for WARN status when runtime is missing in `run_doctor()` (currently `None` at `packages/rentl-core/src/rentl_core/doctor.py:438`; violates spec acceptance for warned checks) (audit round 1)
  - [ ] Fix: Map LLM connectivity failure to connection-category exit code in `run_doctor()` instead of always returning `ExitCode.CONFIG_ERROR` for any failure (`packages/rentl-core/src/rentl_core/doctor.py:446`) (audit round 1)
  - [ ] Fix: Include the workspace directory itself in `check_workspace_dirs()` fix command when workspace is missing (message lists workspace missing but suggestion omits it at `packages/rentl-core/src/rentl_core/doctor.py:226`) (audit round 1)

- [ ] Task 3: Core Phase Explainer Module
  - Create `packages/rentl-core/src/rentl_core/explain.py`
  - Define `PhaseInfo` Pydantic model (name, description, inputs, outputs, prerequisites, config_options)
  - Build phase registry with info for all 7 phases sourced from `PhaseName` enum
  - Implement `get_phase_info(phase_name)` and `list_phases()`
  - Validate phase names against `PhaseName` enum
  - Unit tests for phase info retrieval and validation
  - Acceptance: all 7 phases have complete info; invalid names raise with valid phase list

- [ ] Task 4: Core Help Content Module
  - Create `packages/rentl-core/src/rentl_core/help.py`
  - Define `CommandInfo` Pydantic model (name, brief, detailed_help, args, options, examples)
  - Build command registry from existing CLI commands
  - Implement `get_command_help(name)` and `list_commands()`
  - Unit tests for help content retrieval
  - Acceptance: all existing commands plus new commands are registered; invalid names handled

- [ ] Task 5: CLI Commands — help, doctor, explain
  - Add `rentl help` command to CLI (thin adapter over core help module)
  - Add `rentl doctor` command to CLI (thin adapter over core doctor module, Rich-formatted table)
  - Add `rentl explain` command to CLI (thin adapter over core explain module, Rich-formatted output)
  - Pipe-safe output (detect TTY, degrade to plain text)
  - Exit code mapping from DoctorReport to ExitCode taxonomy
  - Integration tests for CLI invocation of all three commands
  - Acceptance: CLI commands work end-to-end; Rich formatting renders correctly; exit codes correct

- [ ] Task 6: Cross-command Polish and Edge Cases
  - `rentl doctor` outside project dir (no config) — graceful failure
  - `rentl explain badphase` — helpful error with valid phase list
  - `rentl help badcommand` — helpful error with valid command list
  - Verify Rich formatting works and degrades correctly when piped
  - Integration tests for edge cases
  - Acceptance: all edge cases handled gracefully with helpful error messages
