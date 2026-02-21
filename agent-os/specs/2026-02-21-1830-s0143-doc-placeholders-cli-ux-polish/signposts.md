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

## Signpost 4: Init config validation occurs after file write and misses TOML parse errors

- **Task:** Task 5 (audit round 1)
- **Status:** resolved
- **Problem:** Task 5 added validation only after `generate_project` writes `rentl.toml`, so malformed values can persist broken config files. The validation helper also lets `tomllib.TOMLDecodeError` escape instead of normalizing to `ConfigValidationError`.
- **Evidence:** `packages/rentl-core/src/rentl_core/init.py:149-150` writes raw TOML to disk (`toml_content = _generate_toml(answers)` then `config_path.write_text(...)`) before any validation step.
- **Evidence:** `services/rentl-cli/src/rentl/main.py:721-727` calls `generate_project(...)` and only then runs `validate_generated_config(config_path)`.
- **Evidence:** Repro command:
  ```bash
  $ tmpdir=$(mktemp -d) && cd "$tmpdir"
  $ printf 'bad"name\n\n\n\n1\n\n\n\n' | uv run --project /home/trevor/github/rentl rentl init
  ...
  Write this config? [Y/n]: {"data":null,"error":{"code":"validation_error","message":"Expected newline or end of document after a statement (at line 3, column 21)","details":null,"exit_code":11},...}
  $ head -n 4 rentl.toml
  [project]
  schema_version = { major = 0, minor = 1, patch = 0 }
  project_name = "bad"name"
  ```
- **Impact:** Violates `ux/frictionless-by-default`; failed `init` runs can leave users with invalid on-disk config that requires manual cleanup and unclear recovery steps.
- **Solution:** Added `_validate_toml_content` helper in `init.py` that parses and schema-validates the TOML string before any file write. Also wrapped `tomllib.TOMLDecodeError` in `validate_generated_config` as `ConfigValidationError`. Both paths now use the same error type.
- **Resolution:** do-task round 3, 2026-02-21
- **Files affected:** packages/rentl-core/src/rentl_core/init.py, tests/unit/core/test_init.py

## Signpost 5: Pre-write ConfigValidationError is still mapped to runtime_error in CLI init

- **Task:** Task 5 (audit round 2)
- **Status:** resolved
- **Problem:** `generate_project` now validates TOML before write and raises `ConfigValidationError`, but `rentl init` still routes that exception to the generic runtime error path instead of the validation error path.
- **Evidence:** `services/rentl-cli/src/rentl/main.py:722` calls `generate_project(...)`; failures from that call are handled by the broad `except Exception` block at `services/rentl-cli/src/rentl/main.py:772-774`.
- **Evidence:** `_error_from_exception` has no `ConfigValidationError` match and falls back to `runtime_error` in the default case (`services/rentl-cli/src/rentl/main.py:3676-3683`).
- **Evidence:** Repro command output:
  ```bash
  $ uv run python - <<'PY'
  from typer.testing import CliRunner
  from rentl.main import app
  runner = CliRunner()
  with runner.isolated_filesystem():
      result = runner.invoke(app, ["init"], input='bad"name\n\n\n\n1\n\n\n\n')
      print(result.exit_code)
      print(result.stdout.splitlines()[-1])
  PY
  99
  {"data":null,"error":{"code":"runtime_error","message":"Generated TOML is unparseable: Expected newline or end of document after a statement (at line 3, column 21)","details":null,"exit_code":99},...}
  ```
- **Impact:** User input validation failures are mislabeled as runtime failures, which breaks expected CLI semantics and weakens `ux/frictionless-by-default` by returning the wrong exit code for recoverable validation errors.
- **Solution:** Added `except ConfigValidationError` clause in the `init` command exception handling (before `except Exception`) that prints the validation error details and exits with `ExitCode.VALIDATION_ERROR` (11). Added CLI regression test `test_init_command_invalid_project_name_exits_validation_error` asserting exit code 11 and no `rentl.toml` written.
- **Resolution:** do-task round 4, 2026-02-21
- **Files affected:** services/rentl-cli/src/rentl/main.py, tests/unit/cli/test_main.py

## Signpost 6: Export milestone progress events lack regression coverage

- **Task:** Task 6 (audit round 1)
- **Status:** unresolved
- **Problem:** Task 6 requires unit tests for ingest/export milestone progress events, but the test suite only asserts ingest milestone messages.
- **Evidence:** `packages/rentl-core/src/rentl_core/orchestrator.py:1158-1200` emits export `PHASE_PROGRESS` messages (`"Selected ... lines for export"` and `"Wrote ... lines"`), while `tests/unit/core/test_orchestrator.py:1217-1260` only asserts ingest messages and there is no export milestone assertion in that file.
- **Impact:** Leaves Task 6 incomplete and violates `testing/mandatory-coverage` for the new export observability behavior; future regressions could remove export milestone visibility undetected.
- **Solution:** Add a dedicated export milestone test in `tests/unit/core/test_orchestrator.py` that runs `PhaseName.EXPORT` and asserts both export progress messages are emitted as `ProgressEvent.PHASE_PROGRESS`.
