spec_id: s0.1.41
issue: https://github.com/trevorWieland/rentl/issues/125
version: v0.1

# Plan: Documentation Overhaul for v0.1 Release

## Decision Record
rentl is approaching v0.1 release and needs comprehensive documentation for users and contributors. The existing README covers installation and quick start but lacks depth. This spec adds a CHANGELOG, a standalone getting started guide, architecture docs, data schema reference, and license compliance — the final deliverables before v0.1 can ship.

## Tasks
- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit spec artifacts to the issue branch
- [x] Task 2: Create CHANGELOG.md
  - Write v0.1 release notes in Keep a Changelog format
  - Cross-reference `agent-os/product/roadmap.md` for all completed specs
  - Group by capability: pipeline, BYOK, agents, CLI, adapters, observability, QA, config, redaction, benchmark, samples, docs
  - Include known limitations section
  - Files: `CHANGELOG.md`
  - Acceptance: all completed specs appear, format is valid Keep a Changelog
- [x] Task 3: Write Getting Started guide
  - Linear zero-to-playable-patch tutorial in `docs/getting-started.md`
  - Copy-pasteable commands assuming zero context, targeting the fan-translator persona
  - Steps: install → init → configure API key → doctor → prepare source → run pipeline → check output
  - Distinct from README — deeper, more guided, tutorial-style
  - Files: `docs/getting-started.md`
  - Reference: existing README Quick Start, `rentl --help` output
  - Acceptance: all commands reference valid CLI commands, guide works on a fresh machine
  - [x] Fix: Update Step 3 API-key instructions to use the actual init-generated env var (currently `OPENROUTER_API_KEY` in `docs/getting-started.md:69`, but generated projects use `api_key_env = "RENTL_LOCAL_API_KEY"` via `packages/rentl-core/src/rentl_core/init.py:18` and `packages/rentl-core/src/rentl_core/init.py:226`) (audit round 1)
  - [x] Fix: Replace GNU-only `sed -i` usage in `docs/getting-started.md:69` with a cross-platform copy-pasteable method that works on Linux/macOS/WSL as documented (audit round 1)
- [x] Task 4: Write Architecture overview
  - Concise contributor-facing doc in `docs/architecture.md`
  - Cover: 7-phase pipeline diagram, 6 packages, orchestrator flow, agent architecture (TOML profiles, 3-layer prompts, pydantic-ai), data flow (SourceLine → TranslatedLine), port/adapter pattern, storage model
  - Under 300 lines
  - Files: `docs/architecture.md`
  - Reference: `packages/` source code, pipeline orchestrator, agent runtime
  - Acceptance: all referenced names match actual code, under 300 lines
  - [x] Fix: Correct package inventory and dependency-direction statements in `docs/architecture.md` (currently omits `services/rentl-api` and claims library packages depend only on `rentl-schemas`/`rentl-core`). Evidence: `docs/architecture.md:9`, `docs/architecture.md:21`, `services/rentl-api/pyproject.toml:2`, `packages/rentl-agents/pyproject.toml:9`. (audit round 1)
  - [x] Fix: Correct storage-path documentation in `docs/architecture.md` so logs/progress/reports reflect `project.paths.logs_dir` (default `./logs`) rather than `.rentl/logs`; keep `.rentl` scoped to run-state/artifacts paths. Evidence: `docs/architecture.md:217`, `packages/rentl-core/src/rentl_core/init.py:207`, `services/rentl-cli/src/rentl/main.py:2406`, `services/rentl-cli/src/rentl/main.py:2594`, `services/rentl-cli/src/rentl/main.py:2973`. (audit round 1)
  - [x] Fix: Replace invalid BYOK config snippet in `docs/architecture.md` (`[endpoints.default]`) with schema-valid examples (`[endpoint]` or `[endpoints]` + `[[endpoints.endpoints]]`). Evidence: `docs/architecture.md:269`, `packages/rentl-schemas/src/rentl_schemas/config.py:291`, `packages/rentl-schemas/src/rentl_schemas/config.py:637`. (audit round 1)
  - [x] Fix: Correct artifact-index location in the storage model; `index.jsonl` is stored at `.rentl/artifacts/index.jsonl` (global), not `.rentl/artifacts/{run_id}/index.jsonl`. Evidence: `docs/architecture.md:231`, `packages/rentl-io/src/rentl_io/storage/filesystem.py:202`, `packages/rentl-io/src/rentl_io/storage/filesystem.py:512`. (audit round 2)
- [x] Task 5: Write Data Schema reference
  - Document Pydantic models from `rentl-schemas` in `docs/data-schemas.md`
  - Cover: SourceLine, TranslatedLine, per-phase I/O schemas, QA schemas, primitive types
  - Include example JSONL lines from golden artifacts
  - Files: `docs/data-schemas.md`
  - Reference: `packages/rentl-schemas/`, `samples/golden/artifacts/`
  - Acceptance: all documented fields exist in models, all model fields documented
- [x] Task 6: License/legal review and README cross-links
  - Add `license = "MIT"` to all `pyproject.toml` files that lack it
  - Verify no copyrighted text exists in any PyPI-installable package directory
  - Document CC BY-NC-ND benchmark licensing in README or NOTICE
  - Cross-link all new docs (getting-started, architecture, data-schemas, CHANGELOG) from README.md
  - Files: `**/pyproject.toml`, `README.md`
  - Acceptance: all pyproject.toml have license field, README links to all new docs, no bundled copyrighted text
