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
- [ ] Task 2: Create CHANGELOG.md
  - Write v0.1 release notes in Keep a Changelog format
  - Cross-reference `agent-os/product/roadmap.md` for all completed specs
  - Group by capability: pipeline, BYOK, agents, CLI, adapters, observability, QA, config, redaction, benchmark, samples, docs
  - Include known limitations section
  - Files: `CHANGELOG.md`
  - Acceptance: all completed specs appear, format is valid Keep a Changelog
- [ ] Task 3: Write Getting Started guide
  - Linear zero-to-playable-patch tutorial in `docs/getting-started.md`
  - Copy-pasteable commands assuming zero context, targeting the fan-translator persona
  - Steps: install → init → configure API key → doctor → prepare source → run pipeline → check output
  - Distinct from README — deeper, more guided, tutorial-style
  - Files: `docs/getting-started.md`
  - Reference: existing README Quick Start, `rentl --help` output
  - Acceptance: all commands reference valid CLI commands, guide works on a fresh machine
- [ ] Task 4: Write Architecture overview
  - Concise contributor-facing doc in `docs/architecture.md`
  - Cover: 7-phase pipeline diagram, 6 packages, orchestrator flow, agent architecture (TOML profiles, 3-layer prompts, pydantic-ai), data flow (SourceLine → TranslatedLine), port/adapter pattern, storage model
  - Under 300 lines
  - Files: `docs/architecture.md`
  - Reference: `packages/` source code, pipeline orchestrator, agent runtime
  - Acceptance: all referenced names match actual code, under 300 lines
- [ ] Task 5: Write Data Schema reference
  - Document Pydantic models from `rentl-schemas` in `docs/data-schemas.md`
  - Cover: SourceLine, TranslatedLine, per-phase I/O schemas, QA schemas, primitive types
  - Include example JSONL lines from golden artifacts
  - Files: `docs/data-schemas.md`
  - Reference: `packages/rentl-schemas/`, `samples/golden/artifacts/`
  - Acceptance: all documented fields exist in models, all model fields documented
- [ ] Task 6: License/legal review and README cross-links
  - Add `license = "MIT"` to all `pyproject.toml` files that lack it
  - Verify no copyrighted text exists in any PyPI-installable package directory
  - Document CC BY-NC-ND benchmark licensing in README or NOTICE
  - Cross-link all new docs (getting-started, architecture, data-schemas, CHANGELOG) from README.md
  - Files: `**/pyproject.toml`, `README.md`
  - Acceptance: all pyproject.toml have license field, README links to all new docs, no bundled copyrighted text
