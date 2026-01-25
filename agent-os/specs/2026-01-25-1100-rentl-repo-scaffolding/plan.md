# Repository Scaffolding Implementation Plan

Set up the rentl monorepo with modern Python tooling (uv workspaces, ruff, ty), structured packages and services, and three-tier pytest infrastructure.

## Standards Applied

- @agent-os/standards/python/modern-python-314.md
- @agent-os/standards/testing/three-tier-test-structure.md
- @agent-os/standards/global/thin-adapter-pattern.md

## Tasks

### 1. Root Configuration
- [x] Create root `pyproject.toml` with workspace config
- [x] Configure ruff (strict rules) + ty + pytest
- [x] Create `.python-version` (3.14)
- [x] Create `Makefile`

### 2. Package: rentl-schemas
- [x] Create `packages/rentl-schemas/pyproject.toml` (uv build)
- [x] Create `packages/rentl-schemas/src/rentl_schemas/__init__.py`
- [x] Create `packages/rentl-schemas/src/rentl_schemas/version.py`

### 3. Package: rentl-io
- [x] Create `packages/rentl-io/pyproject.toml` (depends on schemas, uv build)
- [x] Create `packages/rentl-io/src/rentl_io/__init__.py`

### 4. Package: rentl-core
- [x] Create `packages/rentl-core/pyproject.toml` (depends on schemas, io, uv build)
- [x] Create `packages/rentl-core/src/rentl_core/__init__.py`
- [x] Create `packages/rentl-core/src/rentl_core/version.py`

### 5. Services: CLI, TUI, API
- [x] Create `services/rentl-cli/pyproject.toml` (depends on core, uv build)
- [x] Create `services/rentl-cli/src/rentl_cli/main.py`
- [x] Create `services/rentl-tui/pyproject.toml` (depends on core, uv build)
- [x] Create `services/rentl-tui/src/rentl_tui/app.py`
- [x] Create `services/rentl-api/pyproject.toml` (depends on core, uv build)
- [x] Create `services/rentl-api/src/rentl_api/main.py`

### 6. Test Infrastructure
- [x] Create `tests/conftest.py`, `tests/unit/conftest.py`
- [x] Create `tests/unit/core/test_version.py`
- [x] Create `tests/unit/cli/test_main.py`

### 7. Verification
- [x] Run `make install` (sync)
- [x] Run `make all` (format, lint, type, unit)
