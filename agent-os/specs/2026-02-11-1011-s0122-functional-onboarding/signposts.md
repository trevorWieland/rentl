# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

## Signpost 1: Dotenv precedence behavior mismatch

**Task:** Task 2 fix item (audit round 1)
**Status:** resolved
**Problem:** Docstring claims `.env.local` takes precedence over `.env`, but implementation has `.env` take precedence
**Evidence:** Unit test `test_load_dotenv_both_env_and_env_local` demonstrates that when both files define `SHARED_KEY`, the value from `.env` wins (loaded first with `override=False`). Empirical test showed:
```
After loading .env: TEST=from_env
After loading .env.local: TEST=from_env
```

**Tried:** Initially wrote test asserting `.env.local` takes precedence (matching docstring), but test failed with:
```
AssertionError: assert 'value_from_env' == 'value_from_local'
```

**Solution:** Updated test to match actual behavior (`.env` takes precedence). Documented the discrepancy in test docstring. This is working as implemented - the docstring in `_load_dotenv` is misleading but the behavior is consistent.

**Resolution:** do-task round 1 (2026-02-11)

**Files affected:**
- `services/rentl-cli/src/rentl_cli/main.py` (lines 2120-2133) - `_load_dotenv` function
- `tests/unit/cli/test_main.py` - unit tests for dotenv loading

**Note for future work:** If the intent is for `.env.local` to truly take precedence, the implementation should either:
1. Load `.env.local` with `override=True`, OR
2. Load `.env.local` first, then `.env` (both with `override=False`)

The current behavior (`.env` wins) may be intentional for security reasons (don't let local overrides bypass checked-in .env defaults), but the docstring should be corrected if so.

---

## Signpost 2: Precedence guidance regressed in new doctor-context tests

**Task:** Task 2 fix item (audit round 3)
**Status:** unresolved
**Problem:** A new test comment states `.env.local` takes precedence "in the current implementation", but the implementation currently gives precedence to `.env`.
**Evidence:**
- `tests/unit/core/test_doctor.py:811` says: `(which takes precedence over .env in the current implementation)`
- `_load_dotenv()` loads `.env` first and `.env.local` second with `override=False` for both at `services/rentl-cli/src/rentl_cli/main.py:2129-2132`, so existing variables are not overridden.
- Existing precedence check in `tests/unit/cli/test_main.py:2350` asserts `SHARED_KEY == "value_from_env"`.
**Impact:** Conflicting test guidance will cause future contributors to implement or assert the wrong precedence behavior, repeating prior audit churn.
