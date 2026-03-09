spec_id: s0.1.47
issue: https://github.com/trevorWieland/rentl/issues/134
version: v0.1

# Plan: Recalibrate Naming Conventions Standard

## Decision Record

The `naming-conventions` standard omits `SCREAMING_SNAKE_CASE` for module-level constants, which is standard Python convention (PEP 8). A 2026-02-17 audit flagged 61 violations that are all correct code. This spec fixes the standard to match reality and corrects any code that was written wrong because the standard implied otherwise.

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Update `naming-conventions.md`
  - Add `SCREAMING_SNAKE_CASE` rule for module-level constants under the Python code naming section
  - Include clear guidance: constants that are immutable and module-scoped use `SCREAMING_SNAKE_CASE`
  - Add real code examples sourced from the rentl codebase (e.g. `CURRENT_SCHEMA_VERSION`, `REQUIRED_COLUMNS`, `OPENROUTER_CAPABILITIES`)
  - File: `agent-os/standards/architecture/naming-conventions.md`
  - [x] Fix: Add explicit module-level constant rule in `agent-os/standards/architecture/naming-conventions.md` near current Python naming rules at lines 36-40 (`SCREAMING_SNAKE_CASE` for immutable, module-scoped constants) to satisfy `architecture/naming-conventions` and spec non-negotiable #2 (audit round 1)
  - [x] Fix: Replace/add examples in `agent-os/standards/architecture/naming-conventions.md` with real in-repo constants (`CURRENT_SCHEMA_VERSION`, `REQUIRED_COLUMNS`, `OPENROUTER_CAPABILITIES`) to satisfy `global/no-placeholder-artifacts` and task scope in `plan.md:17` (audit round 1)
  - [x] Fix: Commit `6950f5b` only changed `plan.md`; implement Task 2 in `agent-os/standards/architecture/naming-conventions.md` and then re-check this task (audit round 2)
- [ ] Task 3: Scan and fix incorrectly-cased constants
  - Grep codebase for module-level assignments that are semantically constants but written in `snake_case` (e.g. `default_max_output_tokens = ...` at module level)
  - Rename any found to `SCREAMING_SNAKE_CASE`
  - Update all import/reference sites
  - Verify tests still pass after renaming
- [ ] Task 4: Update `index.yml`
  - Revise `naming-conventions` description to mention `SCREAMING_SNAKE_CASE` for module-level constants
  - File: `agent-os/standards/index.yml`
- [ ] Task 5: Verify demo steps pass
  - Confirm updated standard contains SCREAMING_SNAKE_CASE rule
  - Grep for 3 previously-flagged constants and confirm they match the updated standard
  - Run `audit-standards.sh --standards naming-conventions --dry-run` to confirm targeting is correct
