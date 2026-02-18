---
standard: prefer-dependency-updates
category: global
score: 88
importance: High
violations_count: 2
date: 2026-02-17
status: violations-found
---

# Standards Audit: Prefer Dependency Updates

**Standard:** `global/prefer-dependency-updates`
**Date:** 2026-02-17
**Score:** 88/100
**Importance:** High

## Summary

Dependency declarations are consistently not pinned to exact versions, and `uv.lock` is present for reproducible installs, so the repository generally avoids stale exact pins. Coverage is good across all package manifests. The remaining gaps are process-oriented and policy-oriented: dependency ranges allow unbounded major upgrades, and the documented/automated install path does not use `uv sync --upgrade`.

## Violations

### Violation 1: External dependencies use lower-bound-only ranges with no upper major bound

- **File:** `pyproject.toml:9`, `pyproject.toml:10`, `services/rentl-api/pyproject.toml:9`, `services/rentl-api/pyproject.toml:10`, `services/rentl-cli/pyproject.toml:14`, `services/rentl-cli/pyproject.toml:15`, `packages/rentl-core/pyproject.toml:9`, `packages/rentl-core/pyproject.toml:10`, `packages/rentl-agents/pyproject.toml:11`, `packages/rentl-agents/pyproject.toml:12`
- **Severity:** Medium
- **Evidence:**
```
openpyxl>=3.1.5
pandas>=3.0.0
fastapi>=0.128.0
uvicorn>=0.40.0
python-dotenv>=1.0.1
pydantic-ai>=1.47.0
httpx>=0.28.1
aiofiles>=24.1.0
```

  (These entries appear across the `dependencies` and `dependency-groups` sections without `<` upper bounds.)
- **Recommendation:** Constrain to compatible ranges that limit major drift, e.g. `openpyxl>=3.1.5,<4.0.0` and `pydantic-ai>=1.47.0,<2.0.0`, then run `uv sync --upgrade` to refresh lock versions on schedule.

### Violation 2: Install/update instructions and target do not use `uv sync --upgrade`

- **File:** `Makefile:43`, `README.md:37`
- **Severity:** Low
- **Evidence:**
```
Makefile:43: @uv sync > /dev/null
README.md:37: uv sync
```

  The standard explicitly recommends frequent updates via `uv sync --upgrade`, but this repository’s primary install path uses plain `uv sync`.
- **Recommendation:** Add a dedicated upgrade target and update docs, e.g. `uv sync --upgrade` for dependency refresh workflows and include it in maintenance checklists.

## Compliant Examples

- `services/rentl-tui/pyproject.toml:7-10` — Uses a local project dependency plus a minimum version spec (`textual>=7.3.0`) instead of an exact pin.
- `packages/rentl-schemas/pyproject.toml:7-9` — Uses `pydantic>=2.12` (range-based constraint, no exact `==` pin).
- `uv.lock:23-27` — Lockfile records exact resolved versions for reproducibility, as required by the standard.

## Scoring Rationale

- **Coverage:** 8 of 9 dependency manifests avoid exact pins and are internally consistent (`>=`-style ranges), so coverage is strong.
- **Severity:** No critical/high-risk runtime defects were found; all issues are upgrade-policy related.
- **Trend:** Policy is uniform across older and newer files, indicating stable but not yet fully mature update strategy.
- **Risk:** Medium operational risk from unbounded major-version progression and less explicit upgrade cadence.
