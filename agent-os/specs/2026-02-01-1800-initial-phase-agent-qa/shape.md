# Initial Phase Agent: QA — Shaping Notes

## Scope

Create the first LLM-based QA agent: a **Style Guide Critic** that evaluates translations against a project's style guide. This agent:
- Identifies violations of tone, formality, terminology preferences
- Works alongside existing deterministic QA checks (Spec 18)
- Produces `QaIssue` records that merge into the unified QA output

## Decisions

### Focus: Style Guide Adherence Only
- This spec focuses solely on style guide enforcement
- Other QA capabilities (accuracy detection, pronoun usage) are future specs
- Single responsibility makes testing and iteration easier

### Style Guide as Project Configuration
- Style guide is a markdown file in project configuration (like `rentl.toml`)
- Simple format: headers for rules, sections for descriptions
- Sample style guide includes localization best practices (e.g., preserving honorifics)

### Graceful Degradation
- If no style guide is provided, agent returns empty issues list
- Deterministic checks still run regardless of style guide presence
- No errors or failures for missing style guide

### Integration with Deterministic Checks
- Both QA approaches produce the same `QaIssue` type
- Deterministic checks use `QaCategory.FORMATTING`
- Style Guide Critic uses `QaCategory.STYLE`
- Orchestrator already has merge logic in place (`_merge_qa_outputs_with_deterministic`)

## Context

- **Visuals:** None (backend logic)
- **References:**
  - Spec 15 (Context Agent) — TOML profile pattern
  - Spec 16 (Pretranslation Agent) — Chunking and agent wrapper pattern
  - Spec 18 (Deterministic QA) — QA phase integration
- **Product alignment:** v0.1 roadmap item (19)

## Standards Applied

- testing/make-all-gate — Verification required before completion
- testing/three-tier-test-structure — Unit/integration test folders
- testing/bdd-for-integration-quality — Given/When/Then style
- python/async-first-design — Agent execution is async
- python/strict-typing-enforcement — Strict Pydantic schemas
- python/pydantic-only-schemas — All I/O uses Pydantic
- architecture/thin-adapter-pattern — Agent is thin wrapper over ProfileAgent
- ux/progress-is-product — Emit progress events during QA
