# Signposts

- **Task:** Task 3
- **Status:** unresolved
- **Problem:** `MigrationRegistry` stores transforms by function name, so distinct migration steps with the same `__name__` collide and the later registration overwrites the earlier transform.
- **Evidence:** `packages/rentl-core/src/rentl_core/migrate.py:43` derives `transform_fn_name` from `__name__`; `packages/rentl-core/src/rentl_core/migrate.py:60` writes `_transforms[transform_fn_name] = transform_fn`; `packages/rentl-core/src/rentl_core/migrate.py:148` resolves transforms only by that name. Repro output:
  - `steps: ['transform', 'transform']`
  - `result: {'schema_version': '0.0.1', 'second': True}`
- **Impact:** Multi-step migrations can execute the wrong transform chain, producing incorrect migrated configs and violating migration correctness guarantees.
