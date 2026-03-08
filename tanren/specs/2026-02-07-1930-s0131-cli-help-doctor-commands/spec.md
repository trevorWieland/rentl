spec_id: s0.1.31
issue: https://github.com/trevorWieland/rentl/issues/31
version: v0.1

# Spec: CLI Help/Doctor Commands

## Problem

Users have no built-in way to troubleshoot setup issues, discover available commands, or learn about pipeline phases. When something goes wrong (missing config, bad API key, unreachable endpoint), the only feedback is a cryptic error at runtime. There's no proactive diagnostic tool and no structured way to explore the CLI.

## Goals

- Provide `rentl help` for command discovery with formatted, detailed output
- Provide `rentl doctor` for proactive environment and configuration diagnostics
- Provide `rentl explain <phase>` for learning what each pipeline phase does
- Make all diagnostic output actionable — every failure includes a fix suggestion

## Non-Goals

- Interactive repair/fix mode (doctor reports, it doesn't fix)
- TUI-based diagnostics (CLI only for this spec)
- Plugin or extension discovery
- Performance profiling or benchmarking

## Acceptance Criteria

### `rentl help`

- [ ] `rentl help` displays a summary of all available commands with brief descriptions
- [ ] `rentl help <command>` displays detailed help for a specific command (args, options, examples)
- [ ] Help output is formatted with Rich (colors, sections) and degrades gracefully to plain text when piped

### `rentl doctor`

- [ ] `rentl doctor` runs all diagnostic checks and prints a pass/fail/warn summary table
- [ ] Checks include: Python version, config file presence and validity, workspace directory structure, API key availability, LLM endpoint connectivity
- [ ] Each failed/warned check includes an actionable fix suggestion
- [ ] Exit code is 0 when all checks pass, non-zero (from ExitCode taxonomy) when any check fails
- [ ] `rentl doctor` works without a valid config (reports config issues as failures rather than crashing)

### `rentl explain <phase>`

- [ ] `rentl explain <phase>` displays what the phase does, its inputs/outputs, prerequisites, and configuration options
- [ ] Phase names are validated against `PhaseName` enum; invalid names produce a helpful error listing valid phases
- [ ] `rentl explain` (no phase) lists all phases with one-line descriptions

### Cross-cutting

- [ ] All diagnostic logic lives in `rentl-core`; CLI layer only formats and displays
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Thin adapter pattern** — All diagnostic logic (config validation, environment checks, connectivity tests) must live in `rentl-core`, not in the CLI layer. CLI commands are thin wrappers that call core functions and format output.
2. **No silent failures** — Every doctor check must produce an explicit pass/fail/warn result with an actionable fix suggestion. No check may silently pass when it can't actually verify the condition.
3. **No new dependencies for help/doctor** — These commands must work with the existing dependency set (typer, rich, pydantic). No new packages for diagnostic functionality.
4. **Exit codes follow existing taxonomy** — Doctor must use the established `ExitCode` enum from `rentl_schemas.exit_codes` (e.g., `CONFIG_ERROR=10`, `CONNECTION_ERROR=30`). No ad-hoc exit codes.
