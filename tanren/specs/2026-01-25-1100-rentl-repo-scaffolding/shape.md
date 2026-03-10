# rentl Repository Scaffolding — Shaping Notes

## Scope

Scaffold the `rentl` monorepo with modern Python tooling and a structure that supports the long-term vision of an agentic localization pipeline.

**Deliverables:**
- Root configuration (`pyproject.toml`, `Makefile`, `.python-version`)
- Internal packages (`rentl-schemas`, `rentl-io`, `rentl-core`)
- Service adapters (`rentl-cli`, `rentl-tui`, `rentl-api`)
- Verification infrastructure (`pytest`, `ruff`, `ty`)

## Decisions

- **Package Structure**: Split into independent packages to avoid circular dependencies. `rentl-schemas` holds types, `rentl-io` holds adapters, `rentl-core` holds logic. Services depend on these.
- **Python Version**: Initially targeted 3.14. Reverted to 3.13 due to Pydantic incompatibility, then upgraded back to 3.14 after environment updates fixed the issue. Final version: **3.14**.
- **Build System**: Used `uv` native build backend (`uv_build`) instead of `hatchling` for consistency.
- **Linting**: Enabled `ruff` preview mode to catch documentation gaps (`DOC` rules).
- **Makefile**: Refactored for clean `✅ passed` / `❌ failed` output to reduce noise.
- **Testing**: Implemented strict 3-tier structure (`unit`, `integration`, `quality`).

## Context

- **Visuals:** None
- **References:** None (Greenfield project)
- **Product alignment:** Aligns with "rentl Localization Pipeline Foundation" knowledge item.

## Standards Applied

- global/thin-adapter-pattern — Services are thin wrappers.
- python/modern-python-314 — Using Python 3.14 stack.
- python/strict-typing-enforcement — Using `ty` strict mode.
- testing/three-tier-test-structure — Using tiered `tests/` layout.
