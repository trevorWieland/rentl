# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation/audit.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.**

---

## Signpost 1: Placeholder replacement introduced non-executable orchestrator examples

- **Task:** Task 2 (audit round 1)
- **Status:** resolved
- **Problem:** `<spec-folder>` placeholders were replaced with a hardcoded path that does not exist in the repo, so documented orchestrator commands fail.
- **Evidence:** `agent-os/docs/WORKFLOW-GUIDE.md:139`, `agent-os/docs/draft-complete.md:133`, `agent-os/docs/draft-concise.md:78`, `agent-os/docs/draft-educational.md:139`, `agent-os/docs/draft-general.md:206` all use `agent-os/specs/2026-02-15-1400-s0142-feature-name`.
- **Evidence:** Running the documented command fails:
  ```bash
  $ ./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-15-1400-s0142-feature-name
  [orch] spec.md not found in agent-os/specs/2026-02-15-1400-s0142-feature-name
  ```
- **Impact:** Violates `ux/copy-pasteable-examples` ("executable without modification") and reintroduces stale-reference risk in onboarding docs.
- **Solution:** Replaced all occurrences with `agent-os/specs/2026-02-05-2240-s0.1.35-cli-exit-codes`, a real spec folder with both `spec.md` and `plan.md`. Verified orchestrator no longer emits `spec.md not found`.
- **Resolution:** do-task round 2, 2026-02-21
- **Files affected:** CONTRIBUTING.md, agent-os/docs/WORKFLOW-GUIDE.md, agent-os/docs/draft-complete.md, agent-os/docs/draft-concise.md, agent-os/docs/draft-educational.md, agent-os/docs/draft-general.md

## Signpost 2: Task 3 verification currently blocked by missing runtime dependency

- **Task:** Task 3 (audit round 1)
- **Status:** resolved
- **Problem:** The required Task 3 verification commands cannot run because CLI startup fails before rendering help output.
- **Evidence:** Running `uv run rentl --help` fails with:
  ```bash
  ModuleNotFoundError: No module named 'griffe'
  ```
- **Evidence:** Trace includes `services/rentl-cli/src/rentl/main.py:40` importing `rentl_agents.providers`, which pulls `pydantic_ai` modules that require `griffe`.
- **Impact:** Blocks the Task 3 acceptance check (`rentl help` and `rentl --help` behavior), so command visibility/docstring gating cannot be verified end-to-end.
- **Solution:** `griffe` 2.0.0 restructured into meta-package (`griffecli` + `griffelib`) that no longer provides the `griffe` Python module. Added `constraint-dependencies = ["griffe<2"]` to `[tool.uv]` in root `pyproject.toml` and re-locked. `griffe==1.15.0` provides the expected `griffe` Python module.
- **Resolution:** do-task round 3, 2026-02-21
- **Files affected:** pyproject.toml, uv.lock

## Signpost 3: Extracted core config handlers crash on malformed TOML shapes

- **Task:** Task 4 (audit round 1)
- **Status:** resolved
- **Problem:** Extracted core helpers assume nested values are TOML tables and call `.get()` on them without type checks, causing uncaught `AttributeError` on malformed-but-parseable configs.
- **Evidence:** `packages/rentl-core/src/rentl_core/migrate.py:344` uses `config_data.get("project", {}).get("schema_version")` and crashes when `project = "oops"`:
  ```bash
  $ uv run python - <<'PY'
  from pathlib import Path
  import tempfile
  from rentl_core.migrate import migrate_config
  with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "rentl.toml"
      p.write_text('project = "oops"\n', encoding="utf-8")
      migrate_config(p)
  PY
  AttributeError: 'str' object has no attribute 'get'
  ```
- **Evidence:** `packages/rentl-core/src/rentl_core/secrets.py:53` and `packages/rentl-core/src/rentl_core/secrets.py:63` call `.get()` on `config_data["endpoint"]` / `config_data["endpoints"]` without guarding type; repro `check_config_secrets({"endpoint": "oops"}, tmp_path)` -> `AttributeError: 'str' object has no attribute 'get'`.
- **Impact:** Violates robustness expectations for CLI boundary logic: malformed config shape produces traceback instead of controlled validation/reporting flow.
- **Solution:** Added explicit `isinstance(..., dict)` / `isinstance(..., list)` guards in `migrate_config` and `check_config_secrets`. Scalar `project` now raises `MigrateError`; scalar `endpoint`/`endpoints` are silently skipped. Added 4 regression tests.
- **Resolution:** do-task round 2, 2026-02-21
- **Files affected:** packages/rentl-core/src/rentl_core/migrate.py, packages/rentl-core/src/rentl_core/secrets.py, tests/unit/core/test_migrate.py, tests/unit/core/test_secrets.py
