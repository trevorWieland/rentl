---
standard: strict-typing-enforcement
category: python
score: 87
importance: High
violations_count: 14
date: 2026-02-18
status: violations-found
---

# Standards Audit: Strict Typing Enforcement

**Standard:** `python/strict-typing-enforcement`
**Date:** 2026-02-18
**Score:** 87/100
**Importance:** High

## Summary

Repository-wide typing usage for schemas is mostly compliant with explicit Pydantic `Field` usage and in-repo schema definitions include validations and descriptions. The codebase does not use `Any` in production Python annotations, and most Pydantic schema fields already use explicit, documented metadata. However, strict `ty` mode is not configured, and `object` is still used in multiple internal type annotations (especially coercion helpers and internal serializers), which conflicts directly with this standard.

## Violations

### Violation 1: `object` used in typed method parameters where explicit unions are feasible

- **File:** `packages/rentl-schemas/src/rentl_schemas/version.py:28`
- **Severity:** Medium
- **Evidence:**
  ```python
  def __lt__(self, other: object) -> bool:
  def __le__(self, other: object) -> bool:
  def __eq__(self, other: object) -> bool:
  def __gt__(self, other: object) -> bool:
  def __ge__(self, other: object) -> bool:
  ```
- **Recommendation:** Replace these with explicit supported comparison inputs (e.g., `other: VersionInfo | tuple[int, int, int] | int` with compatibility handling) and keep `NotImplemented` for unsupported types.

- **Additional file refs (same issue):**
  - `packages/rentl-schemas/src/rentl_schemas/config.py:45`
  - `packages/rentl-schemas/src/rentl_schemas/config.py:84`
  - `packages/rentl-schemas/src/rentl_schemas/config.py:339`
  - `packages/rentl-schemas/src/rentl_schemas/config.py:416`
  - `packages/rentl-schemas/src/rentl_schemas/config.py:445`
  - `packages/rentl-schemas/src/rentl_schemas/config.py:504`
  - `packages/rentl-core/src/rentl_core/migrate.py:227`
  - `services/rentl-cli/src/rentl/main.py:3924`

### Violation 2: `ty` not configured in strict mode

- **File:** `pyproject.toml:61`
- **Severity:** High
- **Evidence:**
  ```toml
  [tool.ty.rules]
  # Strict typing enforcement - escalate warnings to errors
  invalid-argument-type = "error"
  call-non-callable = "error"
  ```
- **Recommendation:** Enable strict mode in `tool.ty` and enforce in CI; the current rules only enforce two checks and do not indicate strict-mode operation.

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/config.py:28` — `Field(..., min_length=1, description="Project workspace directory")`
- `packages/rentl-schemas/src/rentl_schemas/version.py:16` — `Field(..., ge=0, description="Major version number")`
- `packages/rentl-core/src/rentl_core/benchmark/judge.py:34` — `reasoning: str = Field(..., description="Explanation for overall winner")`
- `packages/rentl-schemas/src/rentl_schemas/progress.py:58` — `agent_name: AgentName = Field(..., description="Agent name in snake_case")`
- `packages/rentl-core/src/rentl_core/ports/storage.py:55` — `code: StorageErrorCode = Field(..., description="Storage error code")`

## Scoring Rationale

- **Coverage:** Most schema definitions use `Field` and include descriptions/validators. `Any` and raw schema fields without `Field` were not observed in production paths.
- **Severity:** One high-severity gap (missing `ty` strict configuration) affects whole-project type-safety posture.
- **Trend:** Violations are clustered in existing helper/compatibility code paths, not broad across schema modules; suggests mostly incremental cleanup is needed rather than mass refactor.
- **Risk:** Missing strict mode reduces confidence in type correctness gating; `object` parameters in validators/serializers can hide invalid inputs and reduce useful type-check diagnostics.
