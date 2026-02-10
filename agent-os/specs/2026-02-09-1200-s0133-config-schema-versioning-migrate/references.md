# References: Config Schema Versioning + Migrate

## Implementation Files

- `packages/rentl-schemas/src/rentl_schemas/version.py` — `VersionInfo` model (add comparison operators)
- `packages/rentl-schemas/src/rentl_schemas/config.py` — `RunConfig` and `ProjectConfig` (consumes `schema_version`)
- `packages/rentl-schemas/src/rentl_schemas/validation.py` — Config validation utilities
- `services/rentl-cli/src/rentl_cli/main.py` — CLI entry point, config loading (`_load_run_config`)
- `packages/rentl-core/src/rentl_core/` — Core domain (migration engine goes here)
- `rentl.toml` / `rentl.toml.example` — Config files affected by migration

## New Files

- `packages/rentl-schemas/src/rentl_schemas/migration.py` — `MigrationStep` Pydantic model
- `packages/rentl-core/src/rentl_core/migrate.py` — Migration registry and engine
- `SCHEMA_CHANGELOG.md` — Human-readable schema changelog

## Issues

- [#33 s0.1.33 Config Schema Versioning + Migrate](https://github.com/trevorWieland/rentl/issues/33)

## Dependencies

- s0.1.01 (resolved) — Core config schema foundation
