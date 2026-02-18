---
standard: cli-help-docstring-gating
category: python
score: 72
importance: Medium
violations_count: 4
date: 2026-02-17
status: violations-found
---

# Standards Audit: CLI Help Docstring Gating

**Standard:** `python/cli-help-docstring-gating`
**Date:** 2026-02-17
**Score:** 72/100
**Importance:** Medium

## Summary

The codebase has a single CLI module with most Typer command/help callbacks using `\f` in docstrings to hide internal sections from Typer help output. However, 4 command entrypoints are missing the form-feed gate, reducing consistency of CLI help rendering. Non-compliance is concentrated in one command callback (`main`) and two benchmark commands plus the short `version` command.

## Violations

### Violation 1: Missing `\f` in root callback docstring with internal sections

- **File:** `services/rentl-cli/src/rentl/main.py:243`
- **Severity:** High
- **Evidence:**
  ```
  def main(
      ctx: typer.Context,
      version_flag: bool = typer.Option(
  ) -> None:
      """Rentl CLI.
  
      Raises:
          typer.Exit: When --version flag is used or no command is provided.
      """
  ```
- **Recommendation:** Insert `\f` before `Raises:` to stop Typer from exposing exception details in CLI help, e.g. `"""Rentl CLI.\f\n\nRaises: ...`.

### Violation 2: Missing `\f` in version command docstring

- **File:** `services/rentl-cli/src/rentl/main.py:260`
- **Severity:** Medium
- **Evidence:**
  ```
  @app.command()
  def version() -> None:
      """Display version information."""
  ```
- **Recommendation:** Use the standard gate to keep help output explicit and consistent: `"""Display version information.\f"""`.

### Violation 3: Missing `\f` in benchmark download command docstring

- **File:** `services/rentl-cli/src/rentl/main.py:1200`
- **Severity:** Medium
- **Evidence:**
  ```
  @benchmark_app.command("download")
  def benchmark_download(...):
      """Download and parse evaluation set source material.
  
      Downloads scripts from the evaluation set repository, validates hashes,
      and parses them into rentl-ingestable SourceLine format.
      """
  ```
- **Recommendation:** Add `\f` after the short user-facing description and before any multi-paragraph details: `"""Download and parse evaluation set source material.\f\n\nDownloads..."""`.

### Violation 4: Missing `\f` in benchmark compare command docstring

- **File:** `services/rentl-cli/src/rentl/main.py:1351`
- **Severity:** Medium
- **Evidence:**
  ```
  @benchmark_app.command("compare")
  def benchmark_compare(...):
      """Compare translation outputs head-to-head using LLM judge.
  
      Loads 2+ rentl run outputs, runs all-pairs pairwise comparison,
      computes win rates and Elo ratings, and produces a ranking report.
  
      Uses judge endpoint from rentl.toml config unless overridden.
      """
  ```
- **Recommendation:** Place `\f` after the first sentence or short summary and keep the longer details below it if they are not meant for Typer help.

## Compliant Examples

- `services/rentl-cli/src/rentl/main.py:266` — command `help()` uses `\f` to fence internal `Raises`.
- `services/rentl-cli/src/rentl/main.py:359` — command `doctor()` places `\f` before internal sections.
- `services/rentl-cli/src/rentl/main.py:920` — command `run_pipeline()` includes `\f` and keeps `Raises` hidden.

## Scoring Rationale

- **Coverage:** 10 of 14 Typer-decorated entrypoints (`~71%`) use `\f` correctly.
- **Severity:** Most misses are low-to-medium user-facing/help quality issues; one High item (`main`) includes internal exception docs in default Typer help.
- **Trend:** Recent additions are mixed: newer benchmark commands also miss the separator, so this is not a one-off or legacy-only pattern.
- **Risk:** Functional risk is low because runtime behavior is unchanged, but help output can be inconsistent and may expose internal sections where docs are verbose.
