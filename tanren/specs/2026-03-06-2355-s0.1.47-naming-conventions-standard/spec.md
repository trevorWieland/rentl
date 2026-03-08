spec_id: s0.1.47
issue: https://github.com/trevorWieland/rentl/issues/134
version: v0.1

# Spec: Recalibrate Naming Conventions Standard

## Problem

The `naming-conventions` standard does not mention `SCREAMING_SNAKE_CASE` for module-level constants, causing a standards audit to flag 61 correct Python constants as violations. The standard is wrong; the code is right. Additionally, any constants that were written as `snake_case` because the old standard implied it should be fixed to `SCREAMING_SNAKE_CASE`.

## Goals

- Update the `naming-conventions` standard to explicitly allow and require `SCREAMING_SNAKE_CASE` for module-level constants per PEP 8
- Fix any module-level constants in the codebase that were incorrectly written as `snake_case` due to the faulty standard
- Update `agent-os/standards/index.yml` description to reflect the addition

## Non-Goals

- Renaming correctly-written `SCREAMING_SNAKE_CASE` constants to `snake_case`
- Changing any other naming rules (classes, functions, modules, etc.)
- Re-running the full LLM-based audit suite

## Acceptance Criteria

- [ ] `naming-conventions.md` explicitly allows and requires `SCREAMING_SNAKE_CASE` for module-level constants with a clear rule and at least one real code example
- [ ] Standard is internally consistent — all case styles (snake_case, PascalCase, SCREAMING_SNAKE_CASE) documented without contradiction
- [ ] `index.yml` description updated to mention module-level constants
- [ ] Codebase scanned for module-level constants incorrectly using `snake_case`; any found are renamed to `SCREAMING_SNAKE_CASE` with all call sites updated
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Standard drives code, not vice versa** — The standard is corrected first, then code that was written wrongly due to the faulty standard is fixed to match. Do NOT rename correctly-written `SCREAMING_SNAKE_CASE` constants to `snake_case`.
2. **Internally consistent standard** — The updated `naming-conventions.md` must document all case styles (snake_case, PascalCase, SCREAMING_SNAKE_CASE) without contradiction or ambiguity about when each applies.
3. **No fabricated examples** — Any code snippets added to the standard must reference real rentl code, not invented examples.
