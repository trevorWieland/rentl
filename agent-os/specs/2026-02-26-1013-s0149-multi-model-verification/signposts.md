# Signposts

- **Task:** Task 2 (audit round 1)
- **Status:** resolved
- **Problem:** `endpoint_type` pre-validator assumes string input and calls `.lower()` unconditionally, so null/non-string values raise a raw exception instead of a schema validation error.
- **Evidence:** Validator code at `packages/rentl-schemas/src/rentl_schemas/compatibility.py:56-59` calls `return value.lower()` with no type guard.
- **Evidence:** Repro command output: constructing `VerifiedModelEntry(model_id='x', endpoint_type=None, endpoint_ref='x')` raises `AttributeError: 'NoneType' object has no attribute 'lower'`.
- **Impact:** Invalid registry input can crash compatibility loading paths instead of producing structured validation failures, violating Task 2 acceptance ("invalid entries rejected") behavior.
- **Solution:** Added `isinstance(value, str)` guard in `_coerce_endpoint_type` that raises `ValueError` for non-string inputs, which Pydantic wraps into `ValidationError`. Added two unit tests: `test_entry_rejects_null_endpoint_type` and `test_entry_rejects_non_string_endpoint_type`.
- **Resolution:** do-task round 2
- **Files affected:** `packages/rentl-schemas/src/rentl_schemas/compatibility.py`, `tests/unit/schemas/test_compatibility.py`
