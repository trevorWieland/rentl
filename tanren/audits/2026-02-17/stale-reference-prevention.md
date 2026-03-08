---
standard: stale-reference-prevention
category: ux
score: 76
importance: High
violations_count: 3
date: 2026-02-17
status: violations-found
---

# Standards Audit: Stale Reference Prevention

**Standard:** `ux/stale-reference-prevention`
**Date:** 2026-02-17
**Score:** 76/100
**Importance:** High

## Summary

Cross-reference verification shows partial compliance. Command and config-key coverage is good in most user docs and core implementation, but there are confirmed stale references that can cause real usage problems: environment-variable names in README are not aligned with canonical `.env` documentation, and the custom `rentl help` command advertises and resolves only a subset of real CLI commands. One standards-oriented example file also contains a hardcoded run ID path that is not portable.

Direct `uv run rentl --help` execution was attempted but could not be completed in this environment because CLI startup fails (`Fatal Python error: _Py_HashRandomization_Init...` and UV cache read-only errors).

## Violations

### Violation 1: README documents provider-specific env vars that are not in the project env template

**File:** `README.md:182`

**Severity:** High

**Evidence:**
```
[endpoint]
provider_name = "openrouter"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
...
OPENROUTER_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

**Evidence (canonical config/docs source):**
```
# Local development API key for local LLM endpoints
RENTL_LOCAL_API_KEY=
# Quality evals: API key for the model provider
RENTL_QUALITY_API_KEY=
```

**Recommendation:** Use standardized names in README examples (for example `RENTL_LOCAL_API_KEY` and `RENTL_QUALITY_*`) and include one sentence mapping any provider-specific names only when a compatibility path is intentionally documented.

### Violation 2: `rentl help` command registry omits existing CLI commands

**File:** `packages/rentl-core/src/rentl_core/help.py:23`

**Severity:** High

**Evidence:**
```python
# Command registry with complete information for all commands
_COMMAND_REGISTRY: dict[str, CommandInfo] = {
    "version": ...
    ...
    "explain": ...
}

...
if name not in _COMMAND_REGISTRY:
    raise ValueError(f"Invalid command name '{name}'. Valid commands: {valid_commands}")
```

**Evidence (actual commands in CLI):**
```python
@app.command("check-secrets")
def check_secrets(...):
...

@app.command()
def migrate(...):
...

benchmark_app = typer.Typer(...)
app.add_typer(benchmark_app, name="benchmark")
```

**Recommendation:** Add `check-secrets`, `migrate`, and benchmark command coverage to `_COMMAND_REGISTRY` (including benchmark subcommands as needed), or derive command metadata from Typer app definitions so `rentl help` cannot diverge from real command availability.

### Violation 3: Hardcoded run-ID path in an example intended to be copy-pasteable

**File:** `agent-os/standards/ux/copy-pasteable-examples.md:7`

**Severity:** Medium

**Evidence:**
```
uv run rentl export --input out/run-001/edited_lines.jsonl --output translations.csv --format csv
```

**Recommendation:** Replace the explicit `run-001` path with a dynamic run directory from actual CLI output (e.g., `RUN_DIR=$(ls -d out/run-* | head -1); uv run rentl export --input "$RUN_DIR/edited_lines.jsonl" ...`).

## Compliant Examples

- `docs/getting-started.md:206` — derives runtime output directory from `out/run-*` before exporting.
- `packages/rentl-core/src/rentl_core/init.py:226` — uses `api_key_env = "{StandardEnvVar.API_KEY.value}"` and `StandardEnvVar.API_KEY` is `RENTL_LOCAL_API_KEY`.
- `docs/architecture.md:281` — documents BYOK with `api_key_env = "RENTL_LOCAL_API_KEY"`.
- `README.md:65` — onboarding example uses `RENTL_LOCAL_API_KEY` for the generated `.env` key.

## Scoring Rationale

- **Coverage:** 3 noncompliant patterns across command/help documentation and env-var documentation; remaining audited references align with project standards.
- **Severity:** Two high-severity and one medium-severity findings; key issues are user-facing and can break setup/help workflows.
- **Trend:** Newer user guidance (`docs/getting-started.md`, `docs/architecture.md`) is mostly aligned with standardized env usage; the top-level README and help registry still contain drift.
- **Risk:** Incorrect env-variable guidance can prevent successful pipeline execution on first run, and missing entries in `rentl help` reduce discoverability and trust in built-in command documentation.
