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

- **Task:** Task 2 (audit round 2)
- **Status:** resolved
- **Problem:** `_coerce_endpoint_type` still uses `object` in the validator signature, which violates strict typing rules.
- **Evidence:** Code at `packages/rentl-schemas/src/rentl_schemas/compatibility.py:58` is `def _coerce_endpoint_type(cls, value: object) -> str:`.
- **Evidence:** `strict-typing-enforcement` requires "Never use `Any` or `object` in types" (`agent-os/standards/python/strict-typing-enforcement.md:3`).
- **Impact:** Task 2 remains non-compliant with spec standards despite functional behavior passing tests.
- **Solution:** Changed validator signature to `str | int | float | bool | None` — the explicit union of types a TOML-deserialized value can be in a `mode="before"` validator.
- **Resolution:** do-task round 3
- **Files affected:** `packages/rentl-schemas/src/rentl_schemas/compatibility.py`

- **Task:** Task 3 (audit round 1)
- **Status:** resolved
- **Problem:** `verify_model` uses truthy fallback (`or`) for config overrides, so valid explicit zero values are silently discarded.
- **Evidence:** `temperature = entry.config_overrides.temperature or 0.2` and `top_p = entry.config_overrides.top_p or 1.0` in `packages/rentl-core/src/rentl_core/compatibility/runner.py:262-263`.
- **Impact:** Registry-level overrides cannot force deterministic settings like `temperature=0.0`; verification runs use defaults instead of declared model config.
- **Solution:** Use explicit `is not None` checks for `timeout_s`, `temperature`, `top_p`, and `max_output_tokens` when resolving override values.
- **Resolution:** do-task round 4
- **Files affected:** `packages/rentl-core/src/rentl_core/compatibility/runner.py`

- **Task:** Task 3 (audit round 1)
- **Status:** resolved
- **Problem:** New unit test helper still annotates parameters as `object`, violating strict typing standards.
- **Evidence:** `_side_effect(*args: object, **kwargs: object)` in `tests/unit/core/compatibility/test_runner.py:126-127`.
- **Evidence:** `strict-typing-enforcement` rule states "Never use `Any` or `object` in types" (`agent-os/standards/python/strict-typing-enforcement.md:3`).
- **Impact:** Task 3 remains standards-noncompliant despite functional tests passing.
- **Solution:** Replace `object` annotations with explicit argument types (`str` for args, `str | int | float | bool | None` for kwargs).
- **Resolution:** do-task round 4
- **Files affected:** `tests/unit/core/compatibility/test_runner.py`

- **Task:** Task 4 (audit round 1)
- **Status:** resolved
- **Problem:** `verify-models` does not handle unexpected exceptions from `verify_registry`, so CLI callers get an unstructured failure instead of actionable command-level output.
- **Evidence:** `services/rentl-cli/src/rentl/main.py:3885-3892` calls `asyncio.run(verify_registry(...))` with no surrounding `try/except`.
- **Evidence:** Repro command output (patched verifier): `exit_code: 1`, `exception_type: RuntimeError`, `stdout:` (empty), demonstrating no user-facing diagnostic.
- **Impact:** Runtime/provider failures at verification time can terminate the command without an actionable message, weakening Task 4's "clear and actionable output" guarantee.
- **Solution:** Wrapped `asyncio.run(verify_registry(...))` in `try/except Exception` that prints "Verification error: {exc}" (TTY: rich markup, non-TTY: plain text) and exits with `ExitCode.RUNTIME_ERROR` (99). Added unit test `test_verify_models_runtime_error_returns_actionable_output` that injects a `RuntimeError` and asserts exit code 99 and actionable message.
- **Resolution:** do-task round 5
- **Files affected:** `services/rentl-cli/src/rentl/main.py`, `tests/unit/cli/test_verify_models.py`

- **Task:** Task 5 (audit round 1)
- **Status:** unresolved
- **Problem:** The new compatibility quality test is not actually parameterized by registry entries, and the BDD scenario requests a `model_entry` fixture that is never created.
- **Evidence:** `tests/quality/compatibility/test_model_compatibility.py:43-50` uses `pytest_generate_tests` against `model_entry`, but pytest-bdd's generated scenario does not receive that parametrization.
- **Evidence:** `tests/quality/compatibility/test_model_compatibility.py:76-78` requires `model_entry: VerifiedModelEntry` in the Given step, and execution fails with `fixture 'model_entry' not found`.
- **Evidence:** Repro command output:
  - `LM_STUDIO_API_KEY=dummy RENTL_OPENROUTER_API_KEY=dummy pytest -q tests/quality/compatibility/test_model_compatibility.py --collect-only` → `collected 1 item`
  - `LM_STUDIO_API_KEY=dummy RENTL_OPENROUTER_API_KEY=dummy pytest tests/quality/compatibility/test_model_compatibility.py -q -x` → `E fixture 'model_entry' not found`
- **Impact:** Task 5 does not satisfy "parameterized from the verified-models registry"; the suite cannot execute the intended per-model compatibility verification.
- **Solution:** Define `model_entry` as an explicit pytest fixture parametrized from `_MODEL_ENTRIES` (or equivalent scenario-level parametrization proven to work with pytest-bdd), then verify collection/execution covers each registry model.
- **Files affected:** `tests/quality/compatibility/test_model_compatibility.py`
