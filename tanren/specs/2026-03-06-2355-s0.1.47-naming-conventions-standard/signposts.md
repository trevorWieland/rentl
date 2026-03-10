# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

## Task: Fix lint error (docstring section ordering)

**Status:** blocked

**Problem:** The lint error (D420: Returns section after Raises section) was successfully fixed in `packages/rentl-schemas/src/rentl_schemas/progress.py:558-565`. However, `make check` fails due to 62 pre-existing type errors in test files and some production code. These type errors are not related to the docstring fix but prevent `make check` from passing.

**Evidence:**
```
$ make check
⚡ Running Quick Verification...
🎨 Formatting code...
✅ format Passed
🛠️  Fixing lints...
✅ lint Passed
types checking types...
❌ type Failed

error[invalid-argument-type]: Argument to function `dict_to_toml` is incorrect
    --> tests/unit/cli/test_main.py:2960:27
Expected `ConfigDict`, found `dict[str, dict[str, dict[str, int] | str]]`

error[invalid-argument-type]: Argument to bound method `get` is incorrect
    --> tests/unit/core/test_init.py:373:23
Expected `PhaseName`, found `Literal["ingest"]`

error[invalid-argument-type]: Argument to bound method `__init__` is incorrect
    --> tests/unit/core/test_orchestrator.py:492:27
Expected `list[PhaseAgentProtocol[...]]`, found `list[_NumberAgent]`

... (62 total type errors)
```

**Tried:**
1. Fixed the docstring ordering in `progress.py` - lint now passes ✅
2. Added type annotations to test data in `test_main.py` for ConfigDict - reduced errors from 66 to 62 ✅
3. Added type annotation in `orchestrator.py` for JsonValue - reduced errors from 62 to 61 ✅

**Solution:** The lint error is fixed. The type errors require extensive work to annotate all test data with proper types (ConfigDict, JsonValue) and fix protocol implementation patterns in test stubs. This is beyond the scope of the original lint fix task.

**Files affected:**
- `packages/rentl-schemas/src/rentl_schemas/progress.py` (lint fix - complete)
- `packages/rentl-core/src/rentl_core/orchestrator.py` (type annotation - partial)
- `tests/unit/cli/test_main.py` (type annotations - partial)
- 62 additional type errors across test files

**Next steps:** The lint fix is complete and committed. A separate task should address the type checking errors in the test suite.

---

## Task: Run Demo Step 1

**Status:** unresolved

**Problem:** Demo Step 1 specifies `grep -i "SCREAMING_SNAKE" agent-os/standards/architecture/naming-conventions.md` but the file path doesn't exist. The actual file is at `tanren/standards/architecture/naming-conventions.md`.

**Evidence:**
```
$ grep -i "SCREAMING_SNAKE" agent-os/standards/architecture/naming-conventions.md
grep: agent-os/standards/architecture/naming-conventions.md: No such file or directory

$ grep -i "SCREAMING_SNAKE" tanren/standards/architecture/naming-conventions.md
- Module-level constants: `SCREAMING_SNAKE_CASE` (immutable, module-scoped values)
Use `SCREAMING_SNAKE_CASE` for module-level constants — values that are immutable and defined at the top level of a module.
```

**Root cause:** The demo.md file was not updated during the migration from `agent-os` to `tanren` framework (commit `1740a38 Migrate agent-os to tanren framework`). All references to `agent-os/standards/` should be `tanren/standards/`.

**Files affected:**
- `tanren/specs/2026-03-06-2355-s0.1.47-naming-conventions-standard/demo.md` (needs path fix)
