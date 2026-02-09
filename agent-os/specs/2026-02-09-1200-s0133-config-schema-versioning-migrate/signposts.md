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

- **Task:** Task 5
- **Status:** resolved
- **Problem:** Adding `import contextlib` to `services/rentl-cli/src/rentl_cli/main.py` triggers the type checker to flag 32 pre-existing unused `# type: ignore` directives across multiple test files as warnings, causing `make check` to fail with exit code 1.
- **Evidence:** Running `make type` reports "Found 32 diagnostics" including warnings like `warning[unused-ignore-comment]: Unused blanket type: ignore directive` in `tests/unit/cli/test_main.py:1774`, `tests/unit/schemas/test_migration.py:66/76/86/96`, `tests/unit/schemas/test_version_schema.py:102/105/108`, etc. These warnings did not appear before the contextlib import was added (commit 73d3207 passed `make check` with zero diagnostics).
- **Impact:** Task 5 cannot be marked complete because `make check` fails on the type gate step, even though the actual Task 5 code (auto-migrate functionality) has no type errors and all tests pass.
- **Solution:** Removed all unused `# type: ignore` directives from the affected test files using sed: removed `# type: ignore[call-arg]` from test_migration.py (4 occurrences), `# type: ignore[operator]` from test_version_schema.py (3 occurrences), and `# type: ignore[no-untyped-def]` from test_main.py (4 occurrences). Also removed 2 unused directives from `_dict_to_toml` in main.py. Added type casts in the new unit tests to help the type checker understand nested dict structures. After fixes, `make check` passes with zero diagnostics.
- **Resolution:** do-task round 1 (2026-02-09)
- **Files affected:** `services/rentl-cli/src/rentl_cli/main.py`, `tests/unit/cli/test_main.py`, `tests/unit/schemas/test_migration.py`, `tests/unit/schemas/test_version_schema.py`
