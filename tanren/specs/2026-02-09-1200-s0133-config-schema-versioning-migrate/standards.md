# Standards: Config Schema Versioning + Migrate

## Applicable Standards

1. **pydantic-only-schemas** — Migration steps and changelog entries use Pydantic models
2. **strict-typing-enforcement** — No `Any` or `object` in migration types; all fields use `Field` with descriptions
3. **thin-adapter-pattern** — `rentl migrate` CLI is a thin adapter; migration logic lives in `rentl_core`
4. **trust-through-transparency** — Migration reports what changed clearly via Rich output
5. **frictionless-by-default** — Auto-migrate on load means zero friction for upgrades
6. **three-tier-test-structure** — Unit tests for migration steps/registry, integration tests for CLI command and auto-migrate
7. **naming-conventions** — snake_case for modules/functions/variables, PascalCase for classes
8. **modern-python-314** — Use Python 3.14 features; avoid legacy constructs
