spec_id: s0.1.26
issue: https://github.com/trevorWieland/rentl/issues/27
version: v0.1

# Spec: Standards Review — Declarative Agent Config

## Problem

rentl's declarative agent configuration system (TOML profiles, layered prompts, Pydantic schemas, tool registration, orchestration) is functional and battle-tested across multiple specs, but the conventions are not codified in a formal standard. Without a written standard, new agent profiles may drift from established patterns, auditors have no reference to check against, and onboarding contributors requires reading implementation code rather than documentation.

## Goals

- Codify the existing declarative agent config patterns into a formal standard document
- Audit all existing agent profiles and config schemas against the new standard
- Fix any deviations found during audit without changing runtime behavior

## Non-Goals

- Refactoring the agent config system (this is codification, not redesign)
- Adding new config capabilities or features
- Changing the pipeline execution model
- Modifying the Pydantic schema definitions (unless a deviation is found)

## Acceptance Criteria

- [ ] New standard `architecture/declarative-agent-config` exists with sections covering: agent profile schema, TOML structure, layered prompt system, template variables, tool registration/access, model hints, orchestration config, and pipeline phase config
- [ ] Standard references actual Pydantic model fields and TOML keys (not aspirational)
- [ ] `agent-os/standards/index.yml` updated with the new standard entry
- [ ] All existing agent TOML profiles audited against the standard (deviations documented with evidence)
- [ ] All deviations fixed without changing runtime behavior
- [ ] Existing tests continue to pass (no regressions)
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Standard must be grounded in code** — Every convention in the standard must reference the actual Pydantic schema field or TOML key that enforces it; no aspirational rules without implementation backing
2. **No behavior changes to existing agents** — This is a standards codification + audit, not a refactor; existing agent profiles must produce identical runtime behavior after any fixes
3. **Audit findings must have evidence** — Every deviation found must cite the specific file, field, and expected vs actual value; no vague "this looks wrong" findings
