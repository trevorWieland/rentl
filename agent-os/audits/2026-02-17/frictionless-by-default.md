---
standard: frictionless-by-default
category: ux
score: 58
importance: High
violations_count: 5
date: 2026-02-17
status: violations-found
---

# Standards Audit: Frictionless by Default

**Standard:** `ux/frictionless-by-default`  
**Date:** 2026-02-17  
**Score:** 58/100  
**Importance:** High

## Summary

Initialization is guided and user-friendly for baseline setup, but it is only partially frictionless. The command collects presets and prompts for required values, then immediately writes files without detection-based auto-fills, config preview, or interactive correction of generated settings. The biggest gap is the absence of project/engine/file-language detection and conservative first-run defaults, which means first-run success still depends on user knowledge of expected conventions.

## Violations

### Violation 1: No automatic project/game-engine and source-file detection during init

- **File:** `services/rentl-cli/src/rentl/main.py:569`
- **Severity:** High
- **Evidence:**
  ```python
  project_name = typer.prompt("Project name", default=Path.cwd().name)
  game_name = typer.prompt("Game name", default=game_name_default)
  source_language = typer.prompt("Source language code", default="ja")
  target_languages_input = typer.prompt("Target language codes (comma-separated)", default="en")
  input_format_str = typer.prompt("Input format (jsonl, csv, txt)", default="jsonl")
  ```
- **Recommendation:** Replace hardcoded/manual prompts with auto-detection where possible (e.g., inspect files in `scripts/`, `src/`, `data/`, parse likely format/extensions), then pre-fill detected values with opt-out prompts.

### Violation 2: Source-language default is fixed (`ja`) and does not detect fallback-to-English when uncertain

- **File:** `services/rentl-cli/src/rentl/main.py:574`
- **Severity:** Medium
- **Evidence:**
  ```python
  source_language = typer.prompt("Source language code", default="ja")
  ```
- **Recommendation:** Implement language detection from project files with default-to-`en` when detection fails, while still allowing manual override.

### Violation 3: No pre-acceptance config preview or interactive fix-up step before writing files

- **File:** `services/rentl-cli/src/rentl/main.py:666`
- **Severity:** High
- **Evidence:**
  ```python
  # Build answers
  answers = InitAnswers(...)

  # Generate project
  result = generate_project(answers, Path.cwd())
  ```
- **Recommendation:** Show a proposed config block summary first (model, language, source path, phases), then ask confirmation and allow the user to edit/repair before saving.

### Violation 4: Generated config is written without full post-generation runtime validation in the init command flow

- **File:** `services/rentl-cli/src/rentl/main.py:666` and `packages/rentl-core/src/rentl_core/init.py:124`
- **Severity:** High
- **Evidence:**
  ```python
  result = generate_project(answers, Path.cwd())
  ```
  and
  ```python
  def generate_project(answers: InitAnswers, target_dir: Path) -> InitResult:
      created_files: list[str] = []
      ...
      config_path.write_text(_generate_toml(answers), encoding="utf-8")
      # no Validate-run-config step before write
  ```
- **Recommendation:** Call config schema validation (e.g., `validate_run_config`) after rendering before file write, and if invalid, present errors and guide corrections interactively.

### Violation 5: Default concurrency is set to 8/4, above the standard’s suggested safe default band (3–5)

- **File:** `packages/rentl-core/src/rentl_core/init.py:260`
- **Severity:** Medium
- **Evidence:**
  ```toml
  [concurrency]
  max_parallel_requests = 8
  max_parallel_scenes = 4
  ```
- **Recommendation:** Set safer defaults near 3–5 with an explicit per-install prompt for higher throughput users.

## Compliant Examples

- `services/rentl-cli/src/rentl/main.py:588` — Preset list is shown and user selects a provider, reducing endpoint setup effort.
- `services/rentl-cli/src/rentl/main.py:597` — Repeated custom URL entry with validation loop (`InitAnswers` URL validator) improves input resilience.
- `packages/rentl-core/src/rentl_core/init.py:166` and `:179` — `generate_project` creates required workspace files (`rentl.toml`, `.env`, `input/`, `out/`, `logs/`) in one flow.
- `packages/rentl-core/src/rentl_core/init.py:176` — Config generation includes a concrete next-step instruction list ending with `rentl run-pipeline`.

## Scoring Rationale

- **Coverage:** ~35%. Initialization is guided and outputs next steps, but core frictionless behaviors (auto-detection, preview/review, interactive fix-up, and conservative defaults) are not consistently implemented.
- **Severity:** High due to three High-severity violations that directly affect first-run success path.
- **Trend:** Mixed/plateaued. There are many onboarding and init tests plus provider preset improvements, but no evidence of recent implementation of auto-detection/interactive validation loops in the init pipeline.
- **Risk:** Medium-High. Users can still complete setup, but less-expert users will hit avoidable confusion around required fields and defaults for non-default project layouts.
