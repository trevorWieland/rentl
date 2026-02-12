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

## Task 4: PyPI token authentication failure

**Status:** resolved

**Problem:** Publishing to PyPI fails with 403 Forbidden authentication error. The token was valid but not loaded into the shell environment.

**Evidence:**

The agent ran this command without first sourcing `.env`:
```bash
UV_PUBLISH_TOKEN="${PYPI_TOKEN}" uv publish
```

`PYPI_TOKEN` is defined in `.env` but `.env` is NOT auto-sourced — it must be explicitly loaded. Without `source .env`, `${PYPI_TOKEN}` expands to an empty string, so the actual command sent was `UV_PUBLISH_TOKEN="" uv publish`, which produces the 403.

Proof that the token is not in the environment without sourcing:
```bash
echo "PYPI_TOKEN in env: '${PYPI_TOKEN}'"
# PYPI_TOKEN in env: ''
```

Proof that sourcing .env first works:
```bash
source .env && UV_PUBLISH_TOKEN="${PYPI_TOKEN}" uv publish --dry-run
```
Output:
```
Checking 2 files against https://upload.pypi.org/legacy/
Checking rentl-0.1.0-py3-none-any.whl (30.5KiB)
Checking rentl-0.1.0.tar.gz (29.5KiB)
```
Exit code: 0

**Solution:** Always `source .env` before referencing `$PYPI_TOKEN`. The correct publish command is:
```bash
source .env && UV_PUBLISH_TOKEN="${PYPI_TOKEN}" uv publish
```

**Resolution:** resolve-blockers 2026-02-11 (root cause: missing `source .env`, not an invalid token)

## Task 4: Workspace dependencies not published to PyPI

**Status:** resolved

**Problem:** The `rentl` wheel (CLI package) declares dependencies on `rentl-core`, `rentl-io`, `rentl-llm`, and `rentl-schemas` — none of which exist on PyPI. Publishing only the `rentl` package would make `uvx rentl` fail because pip/uv cannot resolve the workspace-internal dependencies.

**Evidence:**
```bash
curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rentl-core/json"
# 404
curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rentl-io/json"
# 404
curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rentl-llm/json"
# 404
curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/rentl-schemas/json"
# 404
```

Wheel METADATA confirms the dependency chain:
```
Requires-Dist: rentl-core
Requires-Dist: rentl-llm
Requires-Dist: rentl-io
Requires-Dist: rentl-schemas
```

Workspace dependency graph (publish order):
```
rentl-schemas (no internal deps)
  → rentl-core (depends on schemas)
    → rentl-llm (depends on core, schemas)
    → rentl-io (depends on core, schemas)
      → rentl (CLI — depends on core, llm, io, schemas)
```

**Solution:** Expand Task 4 to build and publish all 5 packages in dependency order. Add CI publish script (Task 10) for future releases. User chose multi-package publishing over bundling to preserve workspace architecture and extensibility.

**Resolution:** user via resolve-blockers 2026-02-11
