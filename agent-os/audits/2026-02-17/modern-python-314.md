---
standard: modern-python-314
category: python
score: 72
importance: Medium
violations_count: 6
date: 2026-02-17
status: violations-found
---

# Standards Audit: Modern Python 3.14

**Standard:** `python/modern-python-314`
**Date:** 2026-02-17
**Score:** 72/100
**Importance:** Medium

## Summary
The codebase uses many Python 3.14-era features (notably union types and built-in generics), but core orchestration and agent wiring still rely heavily on legacy `if/elif` dispatch for phase/state logic. Dictionary merge still uses `{**d1, **d2}` in several places, and type-directed branches still use `if`/`elif` chains rather than `match/case`.

Compliance is uneven: modern syntax is present in data model annotations, but key control-flow paths remain tied to pre-3.10 style branching.

## Violations

### Violation 1: Legacy phase dispatch chain in core orchestrator runtime

- **File:** `packages/rentl-core/src/rentl_core/orchestrator.py:499`
- **Severity:** High
- **Evidence:**
  ```python
  if phase == PhaseName.INGEST:
      record = await self._run_ingest(run, ingest_source)
  elif phase == PhaseName.CONTEXT:
      record = await self._run_context(run, execution)
  elif phase == PhaseName.PRETRANSLATION:
      record = await self._run_pretranslation(run, execution)
  elif phase == PhaseName.TRANSLATE:
      record = await self._run_translate(
          run, _require_language(language, phase), execution
      )
  elif phase == PhaseName.QA:
      record = await self._run_qa(
          run, _require_language(language, phase), execution
      )
  elif phase == PhaseName.EDIT:
      record = await self._run_edit(
          run, _require_language(language, phase), execution
      )
  elif phase == PhaseName.EXPORT:
      record = await self._run_export(
          run, _require_language(language, phase), export_target
      )
  ```
- **Recommendation:** Replace with `match phase:` and explicit cases for each `PhaseName` to make dispatch intent explicit and future-proof.

### Violation 2: Phase->phase-guard chains should use match/case

- **File:** `packages/rentl-core/src/rentl_core/orchestrator.py:1776`
- **Severity:** Medium
- **Evidence:**
  ```python
  if phase == PhaseName.INGEST:
      return
  _require_source_lines(run, phase)

  if phase == PhaseName.CONTEXT:
      return

  if _is_phase_enabled(run.config, PhaseName.CONTEXT):
      _require_context_output(run, phase)

  if phase == PhaseName.PRETRANSLATION:
      return

  if phase in {PhaseName.TRANSLATE, PhaseName.EDIT} and _is_phase_enabled(
      run.config, PhaseName.PRETRANSLATION
  ):
      _require_pretranslation_output(run, phase)

  if phase == PhaseName.TRANSLATE:
      return
  ```
- **Recommendation:** Use `match phase:` and structured cases; combine grouped behavior with guard clauses where needed.

### Violation 3: Legacy phase branching in agent wiring

- **File:** `packages/rentl-agents/src/rentl_agents/wiring.py:1288`
- **Severity:** High
- **Evidence:**
  ```python
  if phase == PhaseName.CONTEXT:
      pool = PhaseAgentPool.from_factory(...)
  elif phase == PhaseName.PRETRANSLATION:
      pool = PhaseAgentPool.from_factory(...)
  elif phase == PhaseName.TRANSLATE:
      pool = PhaseAgentPool.from_factory(...)
  elif phase == PhaseName.QA:
      pool = PhaseAgentPool.from_factory(...)
  elif phase == PhaseName.EDIT:
      pool = PhaseAgentPool.from_factory(...)
  else:
      raise ValueError(f"Unsupported phase: {phase.value}")
  ```
- **Recommendation:** Convert this dispatch to `match/case` and keep factory construction grouped and explicit.

### Violation 4: Legacy phase branching when hydrating persisted run artifacts

- **File:** `services/rentl-cli/src/rentl/main.py:2696`
- **Severity:** Medium
- **Evidence:**
  ```python
  if phase == PhaseName.INGEST:
      ...
      continue
  if phase == PhaseName.CONTEXT:
      ...
      continue
  if phase == PhaseName.PRETRANSLATION:
      ...
      continue
  if phase == PhaseName.TRANSLATE and target_language is not None:
      ...
      continue
  if phase == PhaseName.QA and target_language is not None:
      ...
      continue
  if phase == PhaseName.EDIT and target_language is not None:
      ...
      continue
  if phase == PhaseName.EXPORT and target_language is not None:
      ...
      continue
  ```
- **Recommendation:** Convert this branch ladder to `match phase:` for clearer exhaustive handling and reduced accidental omissions.

### Violation 5: Legacy dict merge syntax `{**}` instead of `|`

- **File:** `packages/rentl-agents/src/rentl_agents/prompts.py:183`
- **Severity:** Medium
- **Evidence:**
  ```python
  merged_context = {**prompt_template.default_values, **context}
  ```
- **Recommendation:** Replace with `merged_context = prompt_template.default_values | context`.

### Violation 6: Type-dispatch via `elif isinstance(...)` chains

- **File:** `services/rentl-cli/src/rentl/main.py:2335`
- **Severity:** Medium
- **Evidence:**
  ```python
  if isinstance(value, bool):
      return "true" if value else "false"
  elif isinstance(value, int | float):
      return str(value)
  elif isinstance(value, str):
      ...
  elif isinstance(value, list):
      ...
  elif isinstance(value, dict):
      ...
  ```
- **Recommendation:** Use `match value:` with type patterns and guards where appropriate, e.g., `case bool():`, `case int() | float():`, `case list():`, etc.

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/progress.py:63` — uses modern union syntax: `LanguageCode | None`.
- `packages/rentl-core/src/rentl_core/orchestrator.py:191` — async method uses `async def` and typed returns, consistent with modern async style.
- `packages/rentl-schemas/src/rentl_schemas/version.py` (and many other modules) — uses built-in generics like `list[...]` / `dict[...]` instead of `typing.List`/`typing.Dict`.

## Scoring Rationale

- **Coverage:** Most non-typing legacy patterns are concentrated in phase/type dispatch paths; most schema/model typing and general syntax is modern. Estimated compliance in this standard is ~70%.
- **Severity:** High-severity impact is limited to maintainability and readability; no widespread functional breakage is evident, but core orchestration behavior is deeply tied to verbose branching logic.
- **Trend:** No adoption of `match/case` in the inspected files indicates this standard is not yet consistently applied in newer and older modules.
- **Risk:** Medium practical risk through increased maintenance cost and accidental omission when adding new phases; low immediate runtime risk because behavior is still implemented.
