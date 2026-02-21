spec_id: s0.1.43
issue: https://github.com/trevorWieland/rentl/issues/130
version: v0.1

# Plan: Documentation Placeholders, CLI Surface & UX Polish

## Decision Record
Standards audit (2026-02-17) identified ~80 violations across 7 standards. This spec addresses all violations in a single pass since they share overlapping files (especially main.py and docs). The work is structured so documentation fixes come first (lowest risk), followed by refactoring (medium risk), then new functionality (highest risk).

## Tasks
- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on issue branch and push

- [ ] Task 2: Replace Doc Placeholders & Fix Stale References
  - Replace all `<placeholder>` patterns in README.md, CONTRIBUTING.md, docs/troubleshooting.md, WORKFLOW-GUIDE.md
  - Replace all `<spec-folder>` placeholders in agent-os docs (26 locations across draft-*.md and WORKFLOW-GUIDE.md)
  - Replace `<branch-name>`, `<phase>`, `<command>`, `<output-a>`, `<output-b>`, `<tmp>`, `<name>`, `<run-id>`, `<translated-lines-jsonl>`, `<topic>/<name>.md` placeholders
  - Update README.md:182 env var names from `OPENROUTER_API_KEY`/`OPENAI_API_KEY` to `RENTL_LOCAL_API_KEY`/`RENTL_QUALITY_API_KEY`
  - Fix hardcoded `run-001` in `agent-os/standards/ux/copy-pasteable-examples.md:7`
  - Fix `<command>` placeholder in the standard file itself at `:10`
  - Acceptance: `grep -rn '<[a-z-]*>' README.md CONTRIBUTING.md docs/ WORKFLOW-GUIDE.md` returns zero matches (excluding legitimate HTML tags)

- [ ] Task 3: Update Help Registry & Add \f Docstring Gates
  - Add `check-secrets`, `migrate`, `benchmark` to `_COMMAND_REGISTRY` in `packages/rentl-core/src/rentl_core/help.py`
  - Add `\f` gate to `main` callback docstring at `main.py:243`
  - Add `\f` gate to `version` command docstring at `main.py:260`
  - Add `\f` gate to `benchmark download` docstring at `main.py:1200`
  - Add `\f` gate to `benchmark compare` docstring at `main.py:1351`
  - Test: `rentl help` output includes all registered commands; `rentl --help` hides internal sections

- [ ] Task 4: Extract CLI Logic to Core (thin-adapter-pattern)
  - Extract `migrate` workflow logic from `main.py:3712` to new core module (e.g., `rentl_core/migrate.py`)
  - Extract `check-secrets` validation from `main.py:3574` to new core module (e.g., `rentl_core/secrets.py`)
  - Extract TOML serialization from `main.py:3910` to core (e.g., `rentl_core/config/serialization.py`)
  - Update CLI commands to be thin wrappers calling core functions
  - Unit tests for each extracted module
  - Acceptance: `grep -rn 'from rentl\.' packages/rentl-core/` returns zero matches (excluding test fixtures)

- [ ] Task 5: Improve Init UX (frictionless-by-default)
  - Add auto-detection in `init.py` and `main.py:569`: detect game engine from file patterns, source language from existing files
  - Add config preview display before write at `main.py:666`
  - Add config validation at `init.py:124` before writing generated config
  - Adjust default concurrency at `init.py:260` to safe band (e.g., max_parallel_requests=4, max_parallel_scenes=2)
  - Unit tests for auto-detection logic and config validation

- [ ] Task 6: Add Observability (trust-through-transparency, progress-is-product)
  - Add non-TTY progress output at `main.py:936` — emit structured log events when no TTY detected
  - Add failure context to watcher exit at `main.py:3137`
  - Emit visible log events on retry attempts in `connection.py:198` — log attempt number, backoff delay, error reason
  - Add progress sink to `run-phase` at `main.py:1038-1085`
  - Include error context in phase failure messages at `main.py:1832-1834`
  - Add milestone progress events to ingest at `orchestrator.py:564-621`
  - Add milestone progress events to export at `orchestrator.py:1083-1172`
  - Unit tests verifying log events are emitted on retry, progress events on ingest/export

- [ ] Task 7: Final Integration & Gate Verification
  - Run `make all` and fix any remaining failures
  - Verify all acceptance criteria from spec.md are met
  - Ensure demo steps will pass
