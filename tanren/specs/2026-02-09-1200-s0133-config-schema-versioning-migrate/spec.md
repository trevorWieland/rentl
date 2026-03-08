spec_id: s0.1.33
issue: https://github.com/trevorWieland/rentl/issues/33
version: v0.1

# Spec: Config Schema Versioning + Migrate

## Problem

The `rentl.toml` config has a `schema_version` field but no migration infrastructure. When the schema evolves, users must manually update their config files or face validation errors. This is friction that breaks the "frictionless by default" promise — especially for fan translators who shouldn't need to understand schema changes.

## Goals

- Provide a `rentl migrate` CLI command that upgrades config files to the current schema version
- Auto-migrate outdated configs on load so users never see version-mismatch errors
- Always back up the original config before overwriting
- Maintain a machine-readable schema changelog (migration registry) so every version transition is traceable

## Non-Goals

- Downgrade migrations (rolling back to an older schema version)
- Multi-file config support (only `rentl.toml` is in scope)
- GUI or TUI migration interface (CLI only)
- Config format migration (e.g., TOML to YAML) — format stays TOML

## Acceptance Criteria

- [ ] `rentl migrate` CLI command exists, reads `rentl.toml`, detects current schema version, applies all necessary migration steps, backs up the original to `rentl.toml.bak`, and writes the migrated config
- [ ] `rentl migrate --dry-run` shows what would change without writing
- [ ] Config loading auto-migrates on load: if `schema_version` is older than current, the config is migrated in-memory (and the file is backed up + rewritten) before validation
- [ ] A schema changelog exists as a machine-readable registry of migration steps, mapping version pairs to transform functions
- [ ] Each migration step is a pure function `dict -> dict` registered in the changelog
- [ ] Migration produces clear Rich-formatted output showing: source version, target version, and summary of changes applied
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Migrations must be reversible in data** — every migration step must preserve all original config values (no data loss). A backup is created before any write, but the migration logic itself must not discard fields.
2. **Schema version is the single source of truth** — the `schema_version` field in `rentl.toml` determines which migrations apply. No side-channel version detection.
3. **Migration steps are pure functions** — each step takes a dict and returns a dict, no side effects. The write-to-disk step is separate from the transform step.
4. **Auto-migrate never writes without backup** — when config is auto-migrated on load, the original file must be backed up to `rentl.toml.bak` before any write occurs.
