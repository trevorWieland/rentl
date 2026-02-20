spec_id: s0.1.46
issue: https://github.com/trevorWieland/rentl/issues/133
version: v0.1

# Spec: Codebase Modernization & CI Enforcement

## Problem

The codebase has accumulated 30+ violations across 9 standards: dataclasses instead of Pydantic, legacy if/elif dispatch patterns, loose typing, no CI gate for `make all`, unaddressed deprecation warnings, and scattered compliance gaps in ID formats, API response envelopes, placeholders, and dependency versioning.

## Goals

- Achieve full compliance across all 9 targeted standards
- Migrate all dataclasses (production + test) to Pydantic BaseModel
- Convert all legacy if/elif phase dispatches to match/case
- Enable ty strict mode and resolve all type errors
- Create a CI workflow that enforces `make all` on PRs
- Address all deprecation warnings, ID format gaps, API envelope violations, placeholder artifacts, and dependency version specs

## Non-Goals

- Refactoring beyond what's required for standard compliance
- Adding new features or capabilities
- Addressing standards not in the 9 targeted (e.g., naming-conventions, async-first-design)
- Performance optimization

## Acceptance Criteria

- [ ] All dataclasses in production code migrated to Pydantic BaseModel (15 known across packages/ + services/ + scripts/)
- [ ] All dataclasses in test code migrated to Pydantic BaseModel (16 known across tests/)
- [ ] All if/elif phase dispatches converted to match/case (6 known + any others found)
- [ ] Legacy dict merges (`{**d1, **d2}`) converted to `d1 | d2`
- [ ] isinstance chains converted to match/case where applicable
- [ ] `ty` strict mode enabled in pyproject.toml and all type errors resolved
- [ ] All `object` type annotations replaced with proper types
- [ ] CI workflow (`.github/workflows/ci.yml`) created that runs `make all` on PRs and blocks merge
- [ ] `-W error::DeprecationWarning` added to pytest config in pyproject.toml
- [ ] Deprecation warning flag added to Makefile test targets
- [ ] `HeadToHeadResult.line_id` uses `LineId` type
- [ ] Runtime `run_id` extraction validates as UUIDv7
- [ ] Health endpoint returns `ApiResponse` envelope
- [ ] Placeholder artifact path replaced with proper implementation
- [ ] Obsolete pass-only test stub replaced with real test
- [ ] Dependency version specs use compatible ranges with upper major bounds
- [ ] `make all` passes
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Zero dataclasses remain in production code** — every `@dataclass` must become a Pydantic `BaseModel`; no exceptions, no `# TODO migrate` comments
2. **No legacy if/elif phase dispatches** — all identified if/elif chains converted to `match/case`; no partial conversions
3. **No behavioral regressions** — all existing tests must continue to pass after migration; migrated classes must preserve their public API
4. **CI workflow is real and enforced** — the `make all` CI gate must run on PRs and block merge on failure; not just a YAML file that's never triggered
5. **`make all` passes clean** — no new warnings, no skipped checks, no `SKIP_GATE` overrides
