---
standard: validate-generated-artifacts
category: testing
score: 62
importance: High
violations_count: 6
date: 2026-02-17
status: violations-found
---

# Standards Audit: Validate Generated Artifacts Against Target Schemas

**Standard:** `testing/validate-generated-artifacts`
**Date:** 2026-02-17
**Score:** 62/100
**Importance:** High

## Summary

Compliance is uneven. Newer init and BYOK tests validate generated `rentl.toml` and key output artifacts with schema models, but several older suites still rely on syntax-only assertions or raw dictionary checks. Most gaps are around migration outputs and shared integration helpers that emit config/text fixtures for command execution without explicit schema validation and path-reference checks.

## Violations

### Violation 1: Syntax-only config assertions in core init tests

- **File:** `tests/unit/core/test_init.py:80`
- **Severity:** Medium
- **Evidence:**
  ```python
  with config_path.open("rb") as f:
      config_dict = tomllib.load(f)

  # Basic structure checks
  assert "project" in config_dict
  assert "logging" in config_dict
  ```
  This test validates TOML parse and top-level keys, but does not validate against `RunConfig.model_validate`.
- **Recommendation:** Replace raw key checks with `RunConfig.model_validate(config_dict, strict=True)` (or a helper call) and assert critical fields from the parsed model.

### Violation 2: Seed artifact content checks are not schema-based

- **File:** `tests/unit/core/test_init.py:160`
- **Severity:** High
- **Evidence:**
  ```python
  for line in lines:
      data = json.loads(line)
      assert "scene_id" in data
      assert "route_id" in data
      assert "line_id" in data
      assert "speaker" in data
      assert "text" in data
  ```
  Similar loops in CSV/TXT tests only check token presence and are also susceptible to schema drift.
- **Recommendation:** Validate each generated seed record with `SourceLine.model_validate` (and schema-specific variants where format differs).

### Violation 3: CLI init tests verify generated config with raw dict access

- **File:** `tests/unit/cli/test_main.py:1998`
- **Severity:** Medium
- **Evidence:**
  ```python
  with config_path.open("rb") as f:
      config = tomllib.load(f)
  assert config["endpoint"]["base_url"] == "https://openrouter.ai/api/v1"
  assert config["endpoint"]["api_key_env"] == StandardEnvVar.API_KEY.value
  ```
  Other init tests in this area repeat the same pattern for custom providers and URLs without schema/model validation.
- **Recommendation:** Validate loaded TOML using `RunConfig.model_validate` before asserting endpoint/path fields, and include path-join checks against `config.project.paths`.

### Violation 4: Migration-focused tests do not validate full schema after migration

- **File:** `tests/unit/cli/test_main.py:2701`
- **Severity:** High
- **Evidence:**
  ```python
  project = cast(dict, result["project"])
  schema_version = cast(dict, project["schema_version"])
  assert schema_version["minor"] == 1
  
  with config_path.open("rb") as f:
      updated = tomllib.load(f)
  updated_project = cast(dict, updated["project"])
  updated_schema_version = cast(dict, updated_project["schema_version"])
  ```
  Similar checks are used in `tests/integration/cli/test_migrate.py:160`, `tests/unit/core/test_doctor.py:375`, and `tests/integration/core/test_doctor.py:123`.
- **Recommendation:** Add `RunConfig.model_validate` checks on both post-migration and auto-validated results, not just version tuples.

### Violation 5: Config fixture writers in integration/CLI suites omit schema validation

- **File:** `tests/integration/cli/test_run_pipeline.py:25`
- **Severity:** Medium
- **Evidence:**
  ```python
  file_path = config_path / "rentl.toml"
  file_path.write_text(content, encoding="utf-8")
  return file_path
  ```
  Similar helpers exist in:
  `tests/integration/cli/test_run_phase.py:26`,
  `tests/integration/cli/test_validate_connection.py:24`, and
  `tests/quality/pipeline/test_golden_script_pipeline.py:44`.
- **Recommendation:** Add a shared fixture helper that validates each generated config with `RunConfig`/`validate_run_config` before command execution.

### Violation 6: Preset validation test does not explicitly validate generated config artifact schema or path alignment

- **File:** `tests/quality/cli/test_preset_validation.py:93`
- **Severity:** Medium
- **Evidence:**
  ```python
  # Verify config was created
  assert config_path.exists(), f"Config file not created: {config_path}"

  # Verify .env was created by init
  env_path = project_dir / ".env"
  assert env_path.exists(), f".env file not created by init: {env_path}"
  ```
  The test then relies on `doctor` execution; it does not directly validate the generated config artifact before downstream use.
- **Recommendation:** Load and validate the generated config artifact with `RunConfig.model_validate` (or `validate_run_config`) immediately after init and assert `config.project.paths.input_path` exists as expected.

## Compliant Examples

- `tests/integration/cli/test_init.py:122-143` uses `validate_run_config` on generated TOML payload and fails fast on schema mismatch.
- `tests/integration/cli/test_init.py:146-170` resolves config paths and checks workspace/input/output/logs directory alignment.
- `tests/integration/byok/test_openai_runtime.py:129-137` loads generated config and returns `validate_run_config(payload)`.
- `tests/unit/test_golden_artifacts.py:31-42` validates fixture line records with schema models (`SourceLine.model_validate`, `TranslatedLine.model_validate`, etc.).

## Scoring Rationale

- **Coverage:** ~40% of the relevant artifact-generation flows include explicit schema validation before downstream consumption.
- **Severity:** Several high-severity violations remain in seed-line and migration validation, where malformed payloads can still pass today.
- **Trend:** Newer tests for init/preset runtime integration are stronger, while older helper-based integration suites and migration tests still use structural checks only.
- **Risk:** Medium-high practical risk; schema mismatches can reach runtime execution and produce misleading test outcomes.
