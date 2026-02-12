spec_id: s0.1.39
issue: https://github.com/trevorWieland/rentl/issues/39
version: v0.1

# Plan: Install Verification (uvx/uv tool)

## Decision Record

This spec ensures end users can install rentl via `uvx rentl` — the primary distribution method. The package must be renamed from `rentl-cli` to `rentl` so the uvx command matches naturally, then published to PyPI, and the full install → init → run workflow must be verified on a clean environment.

## Tasks

- [x] Task 1: Save Spec Documentation
- [ ] Task 2: Rename package from rentl-cli to rentl
  - Update `services/rentl-cli/pyproject.toml`: `name = "rentl-cli"` → `name = "rentl"`
  - Update root `pyproject.toml`: `rentl-cli = { workspace = true }` → `rentl = { workspace = true }`
  - Update root `pyproject.toml`: `"rentl-cli"` in dev deps → `"rentl"`
  - Internal module `rentl_cli` stays unchanged (no import changes needed)
  - Test: `uv sync` succeeds, `make all` passes
- [ ] Task 3: Build rentl package
  - Run `uv build --package rentl --no-sources` from workspace root
  - Verify `dist/` contains wheel and sdist
  - Test: build succeeds, artifacts are valid
- [ ] Task 4: Publish rentl to PyPI
  - Set `UV_PUBLISH_TOKEN` from user's PYPI_TOKEN in .env
  - Run `uv publish` from workspace root (or specify dist/)
  - Verify package appears on PyPI at https://pypi.org/project/rentl/
  - Test: `pip show rentl` works after publish
- [ ] Task 5: Verify uvx installation on fresh environment
  - On a machine without rentl installed, run `uvx rentl --version`
  - Test: version outputs correctly (e.g., `rentl v0.1.0`)
- [ ] Task 6: Verify `rentl init` end-to-end
  - Run `uvx rentl init` in a clean directory
  - Verify rentl.toml, .env, workspace directories are created
  - Verify API key prompt works
  - Test: init completes without errors, config is valid
- [ ] Task 7: Verify full pipeline run via uvx
  - Run `uvx rentl run-pipeline` on the initialized project
  - Verify pipeline starts and completes without errors
  - Test: pipeline succeeds end-to-end
- [ ] Task 8: Update README install instructions
  - Document `uvx rentl` as the primary install method
  - Ensure commands match exactly what works
  - Test: README instructions are verbatim what a user should type
- [ ] Task 9: Developer verification
  - Run `make all` from workspace root
  - Verify lint, typecheck, and all test tiers pass
  - Test: `make all` exits with code 0
