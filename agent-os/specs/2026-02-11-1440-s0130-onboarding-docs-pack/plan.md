spec_id: s0.1.30
issue: https://github.com/trevorWieland/rentl/issues/30
version: v0.1

# Plan: Onboarding Docs Pack

## Decision Record

Users discovering rentl on GitHub need a complete, consistent onboarding experience spanning README, CLI help text, troubleshooting docs, and configuration examples. The current state has functional docs but with gaps: CLI help leaks internal `Raises:` docstrings, there's no troubleshooting guide, and cross-references between docs and CLI have drifted. This spec closes those gaps so both fan translators and professional localization teams can go from discovery to first pipeline run without friction.

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Clean up CLI help text
  - Remove `Raises:` docstring sections from user-facing help for all affected commands (use `\f` form-feed character to stop Typer rendering): help, doctor, explain, init, validate-connection, export, run-pipeline, run-phase, status, check-secrets, migrate
  - Fix `benchmark` group description to be a full descriptive sentence
  - Fix `--run-id` help text in `status` command ("Show status for this run" instead of "resume or continue")
  - Fix `--target-language` help text inconsistency between `run-pipeline` and `run-phase`
  - Files: `services/rentl-cli/src/rentl_cli/` command modules
  - Test: `uv run rentl <command> --help` for every command shows no `Raises:` text, all descriptions are meaningful
- [x] Task 3: Rewrite README.md
  - Rewrite with sections: pitch, install (uv sync + uvx), quickstart (init -> doctor -> run-pipeline -> export), command reference table matching `rentl --help` exactly, configuration guide (rentl.toml sections + .env), project structure, development section, contributing/license links
  - Command table must list every command from `rentl --help` with matching descriptions
  - Quickstart must be copy-pasteable with no missing steps
  - Files: `README.md`
  - Test: command table entries match `rentl --help` output
  - [x] Fix: Replace the invalid Quick Start export input path `run-001/edited_lines.jsonl` with a real, generated path/workflow so the step is copy-pasteable (README.md:100; `uv run rentl export --input run-001/edited_lines.jsonl --output /tmp/translations.csv --format csv` fails with `No such file or directory`) (audit round 1)
  - [x] Fix: Quick Start still lacks a copy-pasteable export execution step; `uv run rentl export --help` is documentation lookup, not export workflow. Add an explicit `rentl export --input <translated-lines-jsonl-from-status> --output <path> --format <format>` command sequence using the status-provided path (README.md:103, README.md:106) (audit round 2)
  - [x] Fix: Quick Start export remains non-copy-pasteable because it only describes manual preprocessing and uses placeholder input (`<translated-lines.jsonl>`) instead of executable steps. Add a concrete command sequence that produces a real TranslatedLine JSONL from the run output and then executes `rentl export` with that generated path (README.md:103, README.md:109-115) (audit round 3)
- [x] Task 4: Create troubleshooting doc
  - Create `docs/troubleshooting.md` covering common failure modes:
    - Missing API key (symptom: connection error; cause: env var not set; fix: add to .env)
    - Invalid or missing config (symptom: config parse error; cause: bad TOML or missing file; fix: run rentl init or check syntax)
    - Connection failure (symptom: endpoint unreachable; cause: wrong URL or service down; fix: check base_url and run validate-connection)
    - Schema version mismatch (symptom: migration needed error; cause: config from older version; fix: run rentl migrate)
  - Each entry follows symptom -> cause -> fix pattern
  - Reference `rentl doctor` as the diagnostic starting point
  - Files: `docs/troubleshooting.md`
  - Test: file exists and covers all four failure modes
  - [x] Fix: `docs/troubleshooting.md` hardcodes `RENTL_API_KEY` (docs/troubleshooting.md:27), but current examples are config-driven via `endpoint.api_key_env` (rentl.toml.example:33) and `.env.example` uses `RENTL_LOCAL_API_KEY` (.env.example:2). Update the Missing API Key fix to instruct users to set the env var named by `api_key_env` (with an accurate example) so docs do not contain stale env var references. (audit round 1)
- [ ] Task 5: Cross-reference audit and final consistency pass
  - Verify README command table matches `rentl --help` exactly (command names + descriptions)
  - Verify `rentl.toml.example` config keys are documented in README configuration section
  - Verify `.env.example` variables are documented in README
  - Fix any stale references found across all docs
  - Files: `README.md`, `rentl.toml.example`, `.env.example`
  - Test: no orphaned commands, no undocumented config keys, no undocumented env vars
  - [ ] Fix: README Quick Start export note lists unsupported `json` format (`--format jsonl/json`), but `rentl export --help` only allows `csv|jsonl|txt`; update the note to valid formats to remove stale command guidance (README.md:109) (audit round 1)
