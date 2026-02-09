# Signposts

- **Task:** Task 3
- **Status:** resolved
- **Problem:** `MigrationRegistry` stores transforms by function name, so distinct migration steps with the same `__name__` collide and the later registration overwrites the earlier transform.
- **Evidence:** `packages/rentl-core/src/rentl_core/migrate.py:43` derives `transform_fn_name` from `__name__`; `packages/rentl-core/src/rentl_core/migrate.py:60` writes `_transforms[transform_fn_name] = transform_fn`; `packages/rentl-core/src/rentl_core/migrate.py:148` resolves transforms only by that name. Repro output:
  - `steps: ['transform', 'transform']`
  - `result: {'schema_version': '0.0.1', 'second': True}`
- **Impact:** Multi-step migrations can execute the wrong transform chain, producing incorrect migrated configs and violating migration correctness guarantees.
- **Solution:** Changed `_transforms` dict key from `transform_fn_name` (string) to `(source_version, target_version)` tuple. Each migration edge is now uniquely identified regardless of function name. Updated `get_transform()` to accept a `MigrationStep` and derive the key from its version fields.
- **Resolution:** do-task round 2 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/migrate.py`, `packages/rentl-core/tests/unit/core/test_migrate.py` (added regression test `test_same_function_name_different_migrations`)

- **Task:** Task 3
- **Status:** resolved
- **Problem:** Migration config typing still uses `object` in `ConfigDict`, which violates this spec's `strict-typing-enforcement` rule.
- **Evidence:** `packages/rentl-core/src/rentl_core/migrate.py:11` defines `type ConfigDict = dict[str, object]`; `standards.md` rule 2 requires no `Any` or `object` in migration types.
- **Impact:** The task-level strict typing requirement remains unmet and can mask invalid migration data shapes at type-check time.
- **Solution:** Replaced `object` with a recursively-typed `ConfigValue` alias that explicitly models valid TOML value types: `str | int | float | bool | list[ConfigValue] | dict[str, ConfigValue]`. This preserves flexibility for nested structures while maintaining strict type safety.
- **Resolution:** do-task round 3 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/migrate.py`
