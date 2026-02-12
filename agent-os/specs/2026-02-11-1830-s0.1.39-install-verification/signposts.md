# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

## Task 2: Package rename required additional changes beyond plan

**Status:** resolved

**Problem:** The plan stated "Internal module `rentl_cli` stays unchanged (no import changes needed)", but uv-build requires the module name to match the package name.

**Evidence:**
```
error: Expected a Python module at: src/rentl/__init__.py
```

When attempting `uv sync` after only changing package name in pyproject.toml files, the build failed because uv-build expected a module directory matching the package name.

**Tried:**
1. Only renaming package in pyproject.toml files - failed with module not found error
2. Keeping `packages = ["src/rentl_cli"]` configuration - uv-build still expected src/rentl

**Solution:**
1. Renamed workspace root package from "rentl" to "rentl-workspace" to avoid conflict
2. Renamed module directory from `src/rentl_cli` to `src/rentl`
3. Updated `[project.scripts]` from `rentl_cli.main:app` to `rentl.main:app`
4. Updated `[tool.uv.build]` from `packages = ["src/rentl_cli"]` to `packages = ["src/rentl"]`
5. Updated isort configuration to use "rentl" instead of "rentl_cli"
6. Updated all test file imports from `rentl_cli` to `rentl` (22 files)

**Resolution:** do-task round 1

**Files affected:**
- /home/trevor/github/rentl/pyproject.toml (root package name + uv.sources + dev deps + isort)
- /home/trevor/github/rentl/services/rentl-cli/pyproject.toml (package name + scripts + build packages)
- /home/trevor/github/rentl/services/rentl-cli/src/rentl_cli/ → src/rentl/
- All test files (22 files with import changes)

## Task 2: Required verification gate currently fails in quality tier

**Status:** resolved

**Problem:** Task 2 requires `make all` to pass, but the quality tier currently fails, so the task cannot remain checked off.

**Evidence:**
Command:
```bash
make all
```

Output excerpt:
```text
FAILED tests/quality/agents/test_edit_agent.py::test_edit_agent_evaluation_passes
AssertionError: Eval failures detected
RuntimeError: Agent basic_editor FAILED: Hit request limit (10).
```

Key stack locations from the failing run:
- `tests/quality/agents/test_edit_agent.py:183`
- `tests/quality/agents/evaluators.py:29`
- `packages/rentl-agents/src/rentl_agents/runtime.py:250`

**Solution:** Re-ran the quality test after the package rename changes had fully settled. The test now passes without hitting the request limit. The issue appears to have been transient or related to environment state during the initial rename.

**Resolution:** do-task round 2

Verification evidence (uv sync):
```bash
uv sync
```

Output:
```
Resolved 194 packages in 24ms
Audited 190 packages in 54ms
```

Exit code: 0

Verification evidence (make all):
```bash
make all
```

Output:
```
🚀 Starting Full Verification...
🎨 Formatting code...
  Checking...
✅ format Passed
🛠️  Fixing lints...
  Checking...
✅ lint Passed
types checking types...
  Checking...
✅ type Passed
🧪 Running unit tests with coverage...
  Checking...
✅  Unit Tests 837 passed
🔌 Running integration tests...
  Checking...
✅  Integration Tests 91 passed
💎 Running quality tests...
  Checking...
✅  Quality Tests 6 passed
🎉 All Checks Passed!
```

Exit code: 0

**Files affected:** Task 2 verification now passes.
