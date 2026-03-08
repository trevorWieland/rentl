# Initial QA Checks (Deterministic) — Shaping Notes

## Scope

Implement deterministic QA checks that identify formatting and completeness issues without LLM reasoning. These checks annotate lines with issues that signal to the Editor phase what needs fixing.

**Core formatting checks only (minimal initial set):**
- Line length limits (configurable, no default required)
- Unsupported characters (configurable allowlist)
- Empty translated lines
- Leading/trailing whitespace issues

## Decisions

- **No pipeline failure:** QA checks annotate lines, they don't fail the pipeline. Critical issues at most prevent that specific line from being exported.
- **Configurable line length:** No default value — users must explicitly configure `max_length` in their check parameters.
- **Configurable character allowlist:** Users define allowed character ranges (e.g., `["U+0000-U+007F"]`) with optional common punctuation auto-included.
- **Core checks first:** Start with 4 essential formatting checks; additional checks can be added in future specs.
- **Issues flow to Editor:** QA issues are annotations that inform the Editor phase what to fix in the next iteration.

## Context

- **Visuals:** None — uses existing `QaIssue` schema structure
- **References:** Existing phase agent patterns in `rentl-agents/wiring.py`, QA schemas in `rentl-schemas/qa.py`
- **Product alignment:** Spec 18 in v0.1 roadmap — prerequisite for LLM-based QA agent (spec 19)

## Standards Applied

- **testing/make-all-gate** — Verification required before completion
- **testing/three-tier-test-structure** — Unit tests (<250ms), integration tests (<5s)
- **testing/bdd-for-integration-quality** — Given/When/Then style for integration tests
- **python/pydantic-only-schemas** — All config schemas use Pydantic with Field descriptions
- **python/strict-typing-enforcement** — No `Any`, explicit types everywhere
- **architecture/thin-adapter-pattern** — Checks are pure logic, orchestrator is thin integration layer
