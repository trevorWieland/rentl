spec_id: s0.1.41
issue: https://github.com/trevorWieland/rentl/issues/125
version: v0.1

# Spec: Documentation Overhaul for v0.1 Release

## Problem
rentl is approaching v0.1 release readiness but lacks comprehensive documentation. There is no CHANGELOG, no standalone getting started guide, no architecture overview, no data schema reference, and the license/legal posture has not been audited.

## Goals
- Provide release notes covering all shipped v0.1 specs
- Create a zero-to-playable-patch onboarding tutorial distinct from the README
- Document the architecture for contributors
- Document all data schemas for developers integrating with rentl
- Ensure license compliance across all packages

## Non-Goals
- Rewriting the README from scratch (it already covers installation and quick start)
- Documenting v0.2+ features or roadmap in the new docs
- Creating video tutorials or interactive documentation
- Automated doc generation tooling (manual docs are fine for v0.1)

## Acceptance Criteria
- [ ] CHANGELOG.md exists with v0.1 release notes in Keep a Changelog format, covering all completed specs grouped by capability
- [ ] `docs/getting-started.md` provides a linear zero-to-playable-patch tutorial with copy-pasteable commands
- [ ] `docs/architecture.md` documents the 7-phase pipeline, 6 packages, orchestrator flow, agent architecture, data flow, and port/adapter pattern (under 300 lines)
- [ ] `docs/data-schemas.md` documents all Pydantic models from rentl-schemas with example JSONL lines
- [ ] All `pyproject.toml` files include `license = "MIT"`
- [ ] No copyrighted text is bundled in any PyPI-installable package (benchmark text downloaded at runtime only)
- [ ] Benchmark licensing (CC BY-NC-ND) is documented in README or NOTICE
- [ ] All new docs are cross-linked from README.md
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Getting Started guide is copy-pasteable** — Every command in the guide works on a clean machine with no modifications (verified by running them)
2. **Architecture doc matches code** — Phase names, package names, and class names in the architecture doc are verified against actual source code; no invented or stale references
3. **Schema reference matches Pydantic models** — Every field, type, and description in the schema reference doc is verified against the actual Pydantic model definitions; no stale or invented fields
4. **No copyrighted text ships in PyPI packages** — Katawa Shoujo benchmark text is downloaded at runtime only; no copyrighted content is bundled in any installable package
5. **CHANGELOG covers all shipped specs** — Every completed v0.1 spec appears in the CHANGELOG with accurate descriptions
6. **All new docs cross-linked from README** — Every new document is discoverable from the project README
