spec_id: s0.1.43
issue: https://github.com/trevorWieland/rentl/issues/130
version: v0.1

# Spec: Documentation Placeholders, CLI Surface & UX Polish

## Problem
User-facing documentation contains ~59 `<placeholder>` commands that aren't executable. ENV var names in README are stale. The CLI help registry is incomplete. Business logic for migrate, check-secrets, and TOML serialization is embedded in the CLI surface layer instead of core. CLI docstrings lack `\f` gates. The init command doesn't auto-detect settings or preview config. Non-TTY runs, retry attempts, and ingest/export operations provide no progress visibility.

## Goals
- Replace all doc placeholders with real, copy-pasteable commands
- Align README env var names with canonical names
- Complete the help command registry
- Extract CLI-embedded domain logic to core (thin-adapter-pattern)
- Add `\f` docstring gates to hide internal sections from help output
- Improve init with auto-detection and config preview
- Add observability for non-TTY runs, retries, and ingest/export progress

## Non-Goals
- Full TUI rewrite (deferred to v0.4)
- New CLI commands beyond what's being extracted
- Performance optimization of ingest/export (only adding progress visibility)
- Rewriting existing tests (only adding new tests for new functionality)

## Acceptance Criteria
- [ ] All `<placeholder>` patterns in user-facing docs (README.md, CONTRIBUTING.md, docs/troubleshooting.md, WORKFLOW-GUIDE.md) replaced with real executable commands
- [ ] All `<spec-folder>` placeholders in agent-os docs replaced with concrete example paths
- [ ] README.md env var names updated to canonical `RENTL_LOCAL_API_KEY`/`RENTL_QUALITY_API_KEY`
- [ ] Help registry in `rentl_core/help.py` includes `check-secrets`, `migrate`, and `benchmark` commands
- [ ] Hardcoded `run-001` in copy-pasteable-examples standard replaced with dynamic reference
- [ ] `migrate` workflow logic extracted from CLI to `rentl-core`
- [ ] `check-secrets` validation extracted from CLI to `rentl-core`
- [ ] TOML serialization logic extracted from CLI to `rentl-core`
- [ ] CLI commands become thin wrappers calling core functions
- [ ] `\f` gates added to `main`, `version`, `benchmark download`, and `benchmark compare` docstrings
- [ ] `init` auto-detects project settings (game engine, source language) where possible
- [ ] `init` shows config preview before writing
- [ ] Generated config is validated before save
- [ ] Default concurrency values within safe band
- [ ] Non-TTY progress output emits structured events
- [ ] Watcher exit includes failure context in output
- [ ] LLM retry attempts emit visible log events
- [ ] `run-phase` has progress sink for milestone visibility
- [ ] Phase failure messages include error context
- [ ] Ingest/export operations emit milestone progress events
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No placeholder commands in user-facing docs** — Every `<placeholder>` in README, CONTRIBUTING, troubleshooting, and workflow guides must be replaced with a real, copy-pasteable command. Audit must grep for angle-bracket patterns and find zero in docs.
2. **Extracted core logic must not import CLI surface modules** — Migrate, check-secrets, and TOML serialization logic extracted to `rentl-core` must have zero imports from `rentl` (the CLI service). The dependency arrow points one way: CLI -> Core.
3. **No silent failures in user-facing operations** — Retry attempts, watcher exits, and non-TTY runs must emit visible log/progress events. A user running `rentl` headlessly must be able to diagnose failures from output alone.
4. **No test deletions or modifications to pass gates** — Existing tests must not be weakened, deleted, or have assertions loosened to accommodate changes.
