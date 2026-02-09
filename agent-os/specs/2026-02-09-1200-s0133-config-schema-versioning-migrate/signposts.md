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

- **Task:** Task 4
- **Status:** resolved
- **Problem:** The `rentl migrate` flow reports success but does not update the config's source-of-truth schema version at `project.schema_version`; the seed transform writes a new top-level `schema_version` string instead.
- **Evidence:** `packages/rentl-core/src/rentl_core/migrate.py:198` sets `migrated["schema_version"] = "0.1.0"`; `tests/integration/cli/test_migrate.py:167` expects `migrated_config["project"]["schema_version"]["minor"] == 1`; running `pytest -q tests/integration/cli/test_migrate.py` fails with `E assert 0 == 1`.
- **Impact:** Task 4 acceptance ("applies migrations" to current schema) is not met in practice, and Non-negotiable #2 (`schema_version` field is the single source of truth) is violated by writing a side-channel top-level version field.
- **Solution:** Changed `_migrate_0_0_1_to_0_1_0` to write `project.schema_version` as a dict with `major`, `minor`, `patch` keys set to `0, 1, 0` respectively, matching the expected nested structure. Added defensive copy of project section to avoid mutation.
- **Resolution:** do-task round 4 (2026-02-09)
- **Files affected:** `packages/rentl-core/src/rentl_core/migrate.py`, `packages/rentl-core/tests/unit/core/test_migrate.py` (added regression test `test_seed_migration_no_top_level_schema_version`)
