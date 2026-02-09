spec_id: s0.1.33
issue: https://github.com/trevorWieland/rentl/issues/33
version: v0.1

# Plan: Config Schema Versioning + Migrate

## Decision Record

The `rentl.toml` config already carries a `schema_version` field but has no migration infrastructure. As the schema evolves across v0.1 development, users need a frictionless upgrade path. We're building a migration registry (pure-function steps), a `rentl migrate` CLI command, and auto-migration on config load — so upgrading rentl never breaks existing configs.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on the issue branch

- [x] Task 2: Define Migration Schema Types
  - Add `MigrationStep` Pydantic model to `rentl_schemas` (source_version, target_version, description, transform fn reference)
  - Add comparison operators to `VersionInfo` (`__lt__`, `__le__`, `__eq__`, `__gt__`, `__ge__`) for version ordering
  - Add `CURRENT_SCHEMA_VERSION` constant to `rentl_schemas`
  - Unit tests for version comparison and MigrationStep validation
  - Files: `packages/rentl-schemas/src/rentl_schemas/version.py`, `packages/rentl-schemas/src/rentl_schemas/migration.py`
  - [x] Fix: Add a transform-function reference field on `MigrationStep` (with `Field` description) to satisfy Task 2 contract (`packages/rentl-schemas/src/rentl_schemas/migration.py:25`) (audit round 1)
  - [x] Fix: Add/extend unit tests to validate and serialize the transform-function reference on `MigrationStep` (`tests/unit/schemas/test_migration.py:10`) (audit round 1)

- [x] Task 3: Build Migration Registry & Engine
  - Create `rentl_core/migrate.py` with:
    - `MigrationRegistry` — ordered collection of migration steps
    - `plan_migrations(current_version, target_version)` — returns the chain of steps needed
    - `apply_migrations(config_dict, steps)` — applies each step's pure transform in sequence
  - Register a seed migration: `0.0.1 → 0.1.0` (first real migration for demonstration)
  - Unit tests for registry ordering, chain planning, and transform application
  - Files: `packages/rentl-core/src/rentl_core/migrate.py`
  - [x] Fix: Prevent transform-function collisions by keying lookup on migration edge (or equivalent stable identifier); current name-keyed map can overwrite earlier steps and apply the wrong transform (`packages/rentl-core/src/rentl_core/migrate.py:43`, `packages/rentl-core/src/rentl_core/migrate.py:60`, `packages/rentl-core/src/rentl_core/migrate.py:148`) (audit round 1, see signposts.md: Task 3 transform name collision)
  - [x] Fix: Add regression coverage for two migration steps that share the same `__name__`, proving chain application runs both distinct transforms in order (`packages/rentl-core/tests/unit/core/test_migrate.py`) (audit round 1)
  - [x] Fix: Remove `Any`/untyped `dict` usage from migration type signatures to satisfy `strict-typing-enforcement` (`packages/rentl-core/src/rentl_core/migrate.py:6`, `packages/rentl-core/src/rentl_core/migrate.py:12`, `packages/rentl-core/src/rentl_core/migrate.py:129`) (audit round 1)
  - [x] Fix: Replace `object` in migration config typing with a concrete recursively-typed config value alias to satisfy `strict-typing-enforcement` (`packages/rentl-core/src/rentl_core/migrate.py:11`) (audit round 2)

- [x] Task 4: Add `rentl migrate` CLI Command
  - Add `migrate` command to Typer CLI in `main.py`
  - Accepts `--config` and `--dry-run` options
  - Reads TOML, detects version, plans migrations
  - `--dry-run`: prints planned changes via Rich, exits
  - Normal mode: backs up to `.bak`, applies migrations, writes migrated TOML, prints summary
  - "Already up to date" message when no migrations needed
  - Integration test for the CLI command (dry-run and normal mode)
  - Files: `services/rentl-cli/src/rentl_cli/main.py`

- [ ] Task 5: Auto-Migrate on Config Load
  - Modify `_load_run_config()` in `main.py` to detect outdated schema version
  - When outdated: back up `rentl.toml` to `rentl.toml.bak`, apply migrations, write migrated file, then proceed with validation
  - Log the auto-migration with Rich output (source → target version)
  - Integration test: load an old config, verify backup created and config migrated
  - Files: `services/rentl-cli/src/rentl_cli/main.py`

- [ ] Task 6: Schema Changelog Documentation
  - Create `SCHEMA_CHANGELOG.md` at project root documenting the migration registry in human-readable form
  - Each entry: version pair, date, description of changes
  - Verify changelog stays in sync with the registry (test that every registered migration has a changelog entry)
  - Files: `SCHEMA_CHANGELOG.md`
