# Signposts

- **Task:** Task 2 (audit round 1)
- **Status:** unresolved
- **Problem:** `endpoint_type` pre-validator assumes string input and calls `.lower()` unconditionally, so null/non-string values raise a raw exception instead of a schema validation error.
- **Evidence:** Validator code at `packages/rentl-schemas/src/rentl_schemas/compatibility.py:56-59` calls `return value.lower()` with no type guard.
- **Evidence:** Repro command output: constructing `VerifiedModelEntry(model_id='x', endpoint_type=None, endpoint_ref='x')` raises `AttributeError: 'NoneType' object has no attribute 'lower'`.
- **Impact:** Invalid registry input can crash compatibility loading paths instead of producing structured validation failures, violating Task 2 acceptance ("invalid entries rejected") behavior.
- **Solution:** Guard/coerce `endpoint_type` safely in the validator (or remove the pre-validator and rely on Literal validation), and add a unit test for `endpoint_type=None`/non-string inputs expecting `ValidationError`.
