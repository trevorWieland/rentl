---
standard: config-path-resolution
category: architecture
score: 72
importance: High
violations_count: 3
date: 2026-02-18
status: violations-found
---

# Standards Audit: Config Path Resolution

**Standard:** `architecture/config-path-resolution`
**Date:** 2026-02-18
**Score:** 72/100
**Importance:** High

## Summary

The codebase generally resolves config-related paths from the config file location in the main CLI flow, but there are three out-of-line implementations that bypass or partially ignore the same rules. The highest-risk gaps are in command diagnostics and standalone validation tooling, where config resolution can produce false failures or miss environment variables when configs are run from non-repo directories.

## Violations

### Violation 1: Doctor checks workspace directories relative to config directory instead of resolved workspace_dir

- **File:** `packages/rentl-core/src/rentl_core/doctor.py:264`
- **Severity:** High
- **Evidence:**
  ```python
  # Resolve paths relative to config directory (not CWD)
  workspace_dir = config_dir / config.project.paths.workspace_dir
  output_dir = config_dir / config.project.paths.output_dir
  logs_dir = config_dir / config.project.paths.logs_dir
  ```
- **Recommendation:** Resolve `workspace_dir` the same way as CLI (`config_dir / workspace_dir` when relative), then resolve `output_dir` and `logs_dir` from the resolved `workspace_dir` rather than `config_dir`.

### Violation 2: `validate_agents.py` loads `.env` from current directory, not the config file directory

- **File:** `scripts/validate_agents.py:406`
- **Severity:** Medium
- **Evidence:**
  ```python
  # Load .env file if present
  env_path = Path(".env")
  if env_path.exists():
      load_dotenv(env_path, override=False)
  ```
- **Recommendation:** Load environment files from `args.config.parent` (for both `.env` and `.env.local` if supported), matching `_load_dotenv` behavior in the main CLI.

### Violation 3: Agent path resolver allows absolute prompts/agents paths outside workspace

- **File:** `packages/rentl-agents/src/rentl_agents/wiring.py:1205`
- **Severity:** Medium
- **Evidence:**
  ```python
  if path.is_absolute():
      return path
  return (workspace_dir / path).resolve()
  ```
- **Recommendation:** Disallow absolute paths outside the workspace (or route through the same `_resolve_path` guard used in CLI) so `prompts_dir`/`agents_dir` cannot escape `workspace_dir`.

## Compliant Examples

- `services/rentl-cli/src/rentl/main.py:2209` — `_load_dotenv` loads `.env` from `config_path.parent`.
- `services/rentl-cli/src/rentl/main.py:2224` — `workspace_dir` is resolved relative to config parent when not absolute.
- `services/rentl-cli/src/rentl/main.py:2228` — `input_path`, `output_dir`, and `logs_dir` are resolved via `_resolve_path` against `workspace_dir`.
- `services/rentl-cli/src/rentl/main.py:2243` — `_resolve_path` enforces containment within workspace using `resolved.relative_to(base_dir)`.
- `scripts/validate_agents.py:178` — path resolution for project paths follows the same workspace-rooting approach before config use.

## Scoring Rationale

- **Coverage:** About 60% of inspected path-resolution paths across CLI + auxiliary tooling currently comply with the standard.
- **Severity:** One High and two Medium violations affect both tooling reliability and security boundary assumptions.
- **Trend:** Core CLI resolution is largely compliant, but older/standalone utilities and one shared agent helper still diverge.
- **Risk:** Mis-resolved paths can make configs outside CWD fail checks or silently bypass workspace-boundary expectations, especially during validation and diagnostic workflows.
