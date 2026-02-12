spec_id: s0.1.39
issue: https://github.com/trevorWieland/rentl/issues/39
version: v0.1

# Plan: Install Verification (uvx/uv tool)

## Decision Record

This spec ensures end users can install rentl via `uvx rentl` — the primary distribution method. The package must be renamed from `rentl-cli` to `rentl` so the uvx command matches naturally, then published to PyPI, and the full install → init → run workflow must be verified on a clean environment.

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Rename package from rentl-cli to rentl
  - Update `services/rentl-cli/pyproject.toml`: `name = "rentl-cli"` → `name = "rentl"`
  - Update root `pyproject.toml`: `rentl-cli = { workspace = true }` → `rentl = { workspace = true }`
  - Update root `pyproject.toml`: `"rentl-cli"` in dev deps → `"rentl"`
  - Internal module `rentl_cli` stays unchanged (no import changes needed)
  - Test: `uv sync` succeeds, `make all` passes
  - [x] Fix: Make Task 2 verification pass by fixing `make all` failure at `tests/quality/agents/test_edit_agent.py:183` (`AssertionError: Eval failures detected`) caused by request-limit exhaustion in `packages/rentl-agents/src/rentl_agents/runtime.py:250` (`RuntimeError: Agent basic_editor FAILED: Hit request limit (10)`) (audit round 1; see signposts.md: Task 2, Required verification gate currently fails in quality tier)
  - [x] Fix: Re-run and capture clean evidence for Task 2 required gate (`uv sync` + `make all`) after resolving the quality failure; attach exact command output proving exit code 0 (audit round 1)
  - [x] Fix: Add missing `uv sync` verification evidence for Task 2 in `signposts.md` with exact command output and explicit exit code 0 (`signposts.md:74` currently shows only `make all` evidence) (audit round 2)
- [x] Task 3: Build rentl package
  - Run `uv build --package rentl --no-sources` from workspace root
  - Verify `dist/` contains wheel and sdist
  - Test: build succeeds, artifacts are valid
- [x] Task 4: Build and publish all packages to PyPI
  - All 5 packages must be published (not just rentl) because the CLI depends on workspace packages that don't exist on PyPI yet (see signposts.md: Task 4, Workspace dependencies not published)
  - Build each package: `uv build --package <name> --no-sources` for each
  - **IMPORTANT:** `.env` must be sourced before using `$PYPI_TOKEN` — it is NOT auto-exported to the shell. Use `source .env && UV_PUBLISH_TOKEN="${PYPI_TOKEN}" uv publish ...` (see signposts.md: Task 4, PyPI token authentication failure)
  - Publish in dependency order:
    1. `rentl-schemas` (no internal deps)
    2. `rentl-core` (depends on schemas)
    3. `rentl-llm` (depends on core, schemas) — can publish in parallel with rentl-io
    4. `rentl-io` (depends on core, schemas) — can publish in parallel with rentl-llm
    5. `rentl` (CLI — depends on core, llm, io, schemas)
  - Verify each package appears on PyPI
  - Use lock-step versioning (all packages at 0.1.0)
  - Test: all 5 packages visible on PyPI, `uv pip install rentl` resolves all deps
- [x] Task 5: Verify uvx installation on fresh environment
  - On a machine without rentl installed, run `uvx rentl version`
  - Test: version outputs correctly (e.g., `rentl v0.1.4`)
  - [x] Fix: Implement CLI support for root `--version` so `uvx rentl --version` exits 0 and prints the version required by `spec.md:27` (currently fails with `No such option: --version`; `services/rentl-cli/src/rentl/main.py:229`, `services/rentl-cli/src/rentl/main.py:235`) (audit round 2; see signposts.md: Task 5, `--version` contract mismatch)
  - [x] Fix: Add unit coverage for the `--version` code path in `tests/unit/cli/test_main.py` and persist clean-environment verification evidence (`uvx rentl --version` output + exit code 0) in `signposts.md` before re-checking Task 5 (audit round 2; see signposts.md: Task 5, `--version` contract mismatch)
- [x] Task 6: Verify `rentl init` end-to-end
  - Run `uvx rentl init` in a clean directory
  - Verify rentl.toml, .env, workspace directories are created
  - Verify API key prompt works
  - Test: init completes without errors, config is valid
  - [x] Fix: Add Task 6 command evidence in `signposts.md` with exact `uvx rentl init` output and explicit exit code 0 from a clean directory, including proof of created `rentl.toml`, `.env`, `input/`, `out/`, and `logs/` (audit round 1; `plan.md:44-46`)
  - [x] Fix: Add Task 6 config-valid evidence in `signposts.md` with exact validation command output and explicit exit code 0 (audit round 1; `plan.md:47`)
- [x] Task 7: Verify full pipeline run via uvx
  - Run `uvx rentl run-pipeline` on the initialized project
  - Verify pipeline starts and completes without errors
  - Test: pipeline succeeds end-to-end
  - [x] Fix: Re-run Task 7 verification with valid API credentials and prove `uvx rentl run-pipeline` completes successfully (shell exit code 0, no `error` in output); current evidence records `runtime_error` with `exit_code: 99` (`signposts.md:495`) after writing an invalid key (`signposts.md:490`) (audit round 1; see signposts.md: Task 7, Task verification did not satisfy pipeline success criteria)
  - [x] Fix: Replace `timeout 15 ... run-pipeline` evidence with full end-to-end completion evidence that shows successful pipeline completion output plus explicit shell exit code 0 (`signposts.md:490-498`) (audit round 1; see signposts.md: Task 7, Task verification did not satisfy pipeline success criteria)
- [ ] Task 8: Update README install instructions
  - Document `uvx rentl` as the primary install method
  - Ensure commands match exactly what works
  - Test: README instructions are verbatim what a user should type
  - [ ] Fix: Replace the Step 2 API key snippet in `README.md:61`/`README.md:63-72` with copy-pasteable commands that actually write to `.env`; the current `bash` block only assigns shell variables and leaves `.env` unchanged (violates `copy-pasteable-examples`, `standards.md:8-9`) (audit round 1)
  - [ ] Fix: Re-validate the Quick Start command snippets in `README.md:48-115` in a clean temp project and keep only commands users can run verbatim for Task 8 acceptance (audit round 1)
- [ ] Task 9: Developer verification
  - Run `make all` from workspace root
  - Verify lint, typecheck, and all test tiers pass
  - Test: `make all` exits with code 0
- [ ] Task 10: Add CI publish script
  - Create `scripts/publish.sh` that builds and publishes all packages in correct dependency order
  - Script should: clean dist/, build all 5 packages, publish in order, verify each on PyPI
  - Support `--dry-run` flag for testing without actual upload
  - Test: `scripts/publish.sh --dry-run` succeeds
