---
standard: naming-conventions
category: architecture
score: 76
importance: Medium
violations_count: 61
date: 2026-02-17
status: violations-found
---

# Standards Audit: Naming Conventions

**Standard:** `architecture/naming-conventions`
**Date:** 2026-02-17
**Score:** 76/100
**Importance:** Medium

## Summary

The codebase is mostly consistent for class/type naming, function naming, CLI commands/options, and JSON/JSONL/event field naming where these are used. The primary non-compliance is widespread use of ALL_CAPS module-level variables for settings/constants where the standard requires snake_case variable names, plus one non-snake module filename. This is largely stylistic but creates mixed naming signals across packages.

## Violations

### Violation 1: Script/module filename is not snake_case

- **File:** `agent-os/scripts/list-candidates.py:1`
- **Severity:** Medium
- **Evidence:**
  ```python
  #!/usr/bin/env python3
  """List unblocked spec candidates from GitHub issues.
  ```
- **Recommendation:** Rename the file to `list_candidates.py` (or move to a similarly named package module path).

### Violation 2: Uppercase module-level constants for CLI options

- **File:** `services/rentl-cli/src/rentl/main.py:176`
- **Severity:** Low
- **Evidence:**
  ```python
  INPUT_OPTION = typer.Option(...)
  OUTPUT_OPTION = typer.Option(...)
  FORMAT_OPTION = typer.Option(...)
  UNTRANSLATED_POLICY_OPTION = typer.Option(...)
  INCLUDE_SOURCE_TEXT_OPTION = typer.Option(...)
  ```
- **Recommendation:** Rename these constants to snake_case (e.g., `input_option`, `output_option`, `format_option`) if the project enforces variable naming strictly.

### Violation 3: Uppercase module-level variable in schema version module

- **File:** `packages/rentl-schemas/src/rentl_schemas/version.py:10`
- **Severity:** Low
- **Evidence:**
  ```python
  CURRENT_SCHEMA_VERSION = (0, 1, 0)
  ```
- **Recommendation:** Use `current_schema_version`.

### Violation 4: Uppercase module-level constants in schema primitives

- **File:** `packages/rentl-schemas/src/rentl_schemas/primitives.py:11`
- **Severity:** Low
- **Evidence:**
  ```python
  HUMAN_ID_PATTERN = r"^[a-z]+(?:_[0-9]+)+$"
  ISO_8601_PATTERN = (
  LANGUAGE_CODE_PATTERN = r"^[a-z]{2}(?:-[A-Z]{2})?$"
  EVENT_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
  PIPELINE_PHASE_ORDER = [
  ```
- **Recommendation:** Rename to snake_case names such as `human_id_pattern`, `pipeline_phase_order`, etc.

### Violation 5: Uppercase module-level variable in storage schema module

- **File:** `packages/rentl-schemas/src/rentl_schemas/storage.py:21`
- **Severity:** Low
- **Evidence:**
  ```python
  CHECKSUM_PATTERN = r"^[a-f0-9]{64}$"
  ```
- **Recommendation:** Prefer `checksum_pattern`.

### Violation 6: Uppercase module-level variable in schema redaction module

- **File:** `packages/rentl-schemas/src/rentl_schemas/redaction.py:48`
- **Severity:** Low
- **Evidence:**
  ```python
  DEFAULT_PATTERNS = [
  ```
- **Recommendation:** Use `default_patterns`.

### Violation 7: Camel/PascalCase keys in data mapping

- **File:** `packages/rentl-schemas/src/rentl_schemas/exit_codes.py:77`
- **Severity:** Medium
- **Evidence:**
  ```python
  DOMAIN_PREFIXES: dict[str, str] = {
      "OrchestrationErrorCode": "orchestration",
      "IngestErrorCode": "ingest",
      "ExportErrorCode": "export",
      "StorageErrorCode": "storage",
  }
  ```
- **Recommendation:** Use snake_case keys to align with JSON/contract naming (`"orchestration_error_code"`, `"ingest_error_code"`, etc.).

### Violation 8: Uppercase module-level constants across core runtime modules

- **File:** `packages/rentl-core/src/rentl_core/version.py:5`
- **Severity:** Low
- **Evidence:**
  ```python
  VERSION = VersionInfo(major=0, minor=1, patch=8)
  _REGISTRY = MigrationRegistry()
  _LLM_PHASES = {
  ```
- **Recommendation:** Rename to `version`, `_registry`, `_llm_phases`.

### Violation 9: Uppercase module-level constants in export adapters

- **File:** `packages/rentl-io/src/rentl_io/export/csv_adapter.py:22`
- **Severity:** Low
- **Evidence:**
  ```python
  REQUIRED_COLUMNS = ("line_id", "text")
  OPTIONAL_COLUMNS = ("scene_id", "speaker", "source_text", "metadata")
  RESERVED_COLUMNS = set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
  ```
- **Recommendation:** Use `required_columns`, `optional_columns`, etc.

### Violation 10: Uppercase module-level constants in ingest adapters

- **File:** `packages/rentl-io/src/rentl_io/ingest/csv_adapter.py:21`
- **Severity:** Low
- **Evidence:**
  ```python
  REQUIRED_COLUMNS = ("line_id", "text")
  OPTIONAL_COLUMNS = ("scene_id", "speaker", "metadata")
  KNOWN_COLUMNS = set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
  EXPECTED_FIELDS = [*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS]
  CSV_HEADER_EXAMPLE = "line_id,text,scene_id,speaker,metadata"
  CSV_ROW_EXAMPLE = 'line_1,Hello,scene_1,Alice,"{""tone"":...}"
  ```
- **Recommendation:** Rename these to snake_case module variables.

### Violation 11: Uppercase module-level constants in JSONL ingest adapter

- **File:** `packages/rentl-io/src/rentl_io/ingest/jsonl_adapter.py:20`
- **Severity:** Low
- **Evidence:**
  ```python
  ALLOWED_KEYS = {"line_id", "route_id", "scene_id", "speaker", "text", "metadata"}
  EXPECTED_FIELDS = [
  JSONL_EXAMPLE = (
  ```
- **Recommendation:** Use `allowed_keys`, `expected_fields`, `jsonl_example`.

### Violation 12: Uppercase constants for provider capabilities

- **File:** `packages/rentl-agents/src/rentl_agents/providers.py:32`
- **Severity:** Low
- **Evidence:**
  ```python
  OPENROUTER_CAPABILITIES = ProviderCapabilities(...)
  OPENAI_CAPABILITIES = ProviderCapabilities(...)
  LOCAL_CAPABILITIES = ProviderCapabilities(...)
  GENERIC_CAPABILITIES = ProviderCapabilities(...)
  ```
- **Recommendation:** Use `openrouter_capabilities`, `openai_capabilities`, etc.

### Violation 13: Uppercase module variables in agent runtime/templates

- **File:** `packages/rentl-agents/src/rentl_agents/runtime.py:47`
- **Severity:** Low
- **Evidence:**
  ```python
  DEFAULT_MAX_OUTPUT_TOKENS = 4096
  _VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")
  TEMPLATE_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")
  ```
- **Recommendation:** Rename to `default_max_output_tokens`, `_variable_pattern`, and `template_variable_pattern`.

### Violation 14: Uppercase module variables in tests

- **File:** `tests/quality/pipeline/test_golden_script_pipeline.py:41`
- **Severity:** Low
- **Evidence:**
  ```python
  _GOLDEN_SUBSET_SIZE = 1
  ```
- **Recommendation:** Use `golden_subset_size` if consistent naming is required in tests too.

### Violation 15: Additional module-level ALL_CAPS in tests

- **File:** `tests/unit/test_golden_artifacts.py:16`
- **Severity:** Low
- **Evidence:**
  ```python
  GOLDEN_DIR = Path(__file__).parent.parent.parent / "samples" / "golden"
  ARTIFACTS_DIR = GOLDEN_DIR / "artifacts"
  U7 = UUID("01945b78-c431-7000-8000-000000000001")
  ```
- **Recommendation:** Use snake_case names (`golden_dir`, `artifacts_dir`, `u7`) unless test data intentionally follows legacy notation.

### Violation 16: Additional uppercase test/config constants

- **File:** `tests/integration/benchmark/test_judge_flow.py:17`
- **Severity:** Low
- **Evidence:**
  ```python
  FEATURES_DIR = Path(__file__).parent.parent.parent / "features" / "benchmark"
  VALID_TEST_CONFIG_TOML = """[orchestrator]..."""
  ```
- **Recommendation:** Use `features_dir` and `valid_test_config_toml`.

### Violation 17: Uppercase module variable in LLM layer

- **File:** `packages/rentl-llm/src/rentl_llm/openai_runtime.py:24`
- **Severity:** Low
- **Evidence:**
  ```python
  DEFAULT_MAX_OUTPUT_TOKENS = 4096
  ```
- **Recommendation:** Use `default_max_output_tokens`.

## Compliant Examples

- `services/rentl-cli/src/rentl/main.py:358` — `def run_pipeline(...):` uses snake_case function naming.
- `packages/rentl-schemas/src/rentl_schemas/events.py:20` — `class RunEvent(StrEnum):` uses PascalCase.
- `services/rentl-cli/src/rentl/main.py:724` — command name is kebab-case (`@app.command("validate-connection")`).
- `packages/rentl-schemas/src/rentl_schemas/events.py:23` — event value is snake_case (`"run_started"`).
- `packages/rentl-core/src/rentl_core/ports/export.py:30` — event enum names and data payload fields are snake_case based.

## Scoring Rationale

- **Coverage:** Most violations are concentrated in module-level variable declarations; class/type/function naming, command naming, and event/payload naming are largely consistent.
- **Severity:** Low to medium overall; no critical/high functional regressions were found during this naming audit.
- **Trend:** Mixed style exists in both older and newer code paths, so this is a repository-wide pattern rather than a recent regression.
- **Risk:** Consistency risk is moderate for maintainability (searchability, onboarding, and automated style enforcement) but low for runtime behavior.
