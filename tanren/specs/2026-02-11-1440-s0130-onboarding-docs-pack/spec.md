spec_id: s0.1.30
issue: https://github.com/trevorWieland/rentl/issues/30
version: v0.1

# Spec: Onboarding Docs Pack

## Problem

A user who discovers the rentl GitHub repo lacks a complete, consistent path from discovery to first pipeline run. The README is functional but doesn't cover configuration in depth, CLI help text leaks internal docstring details, there's no troubleshooting guide, and cross-references between docs and CLI output have drifted.

## Goals

- A user who finds the GitHub repo has everything they need to use rentl to its fullest potential
- Documentation (Markdown files), CLI help commands, and configuration examples are fully consistent with each other
- Common failure modes are documented with clear symptom/cause/fix patterns

## Non-Goals

- API documentation (rentl-api is future/placeholder)
- Package-level READMEs for internal packages (rentl-core, rentl-schemas, etc.)
- Tutorial videos or non-Markdown documentation formats
- Changes to CLI behavior or functionality (only help text and descriptions)

## Acceptance Criteria

- [ ] README.md rewrite covering: pitch, install (uv sync + uvx), quickstart (init -> doctor -> run-pipeline -> export), full command reference table, configuration guide (rentl.toml + .env), project structure, and contributing link
- [ ] CLI help consistency: every command's --help output has a clear, meaningful description and all argument/option help text is filled in (no empty, auto-generated, or internal-only descriptions)
- [ ] Troubleshooting doc: docs/troubleshooting.md covering common failure modes (missing API key, invalid config, connection failures, schema migration needed) with symptom/cause/fix for each, referencing rentl doctor
- [ ] Cross-reference audit: README command table matches rentl --help output exactly; rentl.toml.example matches config docs in README; .env.example matches environment variable docs
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No orphaned commands** — Every CLI command listed in `--help` must appear in README.md and vice versa; no command exists in one place but not the other
2. **Zero-to-pipeline path in README** — The README quickstart must be a complete, copy-pasteable path from install to first pipeline run with no missing steps
3. **CLI help text is self-sufficient** — Every command and subcommand must have a meaningful `--help` description (not just the function name); a user who only reads `--help` can use the command correctly
4. **No stale references** — All docs must reference actual current commands, config keys, and file paths; no references to removed/renamed features
