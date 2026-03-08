---
standard: thin-adapter-pattern
category: architecture
score: 62
importance: High
violations_count: 3
date: 2026-02-17
status: violations-found
---

# Standards Audit: Thin Adapter Pattern

**Standard:** `architecture/thin-adapter-pattern`
**Date:** 2026-02-17
**Score:** 62/100
**Importance:** High

## Summary

The CLI layer contains multiple command implementations that perform domain-like validation, parsing, orchestration, and serialization. This means significant business logic is not fully centralized in `rentl-core`. `rentl-tui` and `rentl-api` are small wrappers and adhere to the pattern, but `rentl-cli` has substantial non-thin sections. The codebase is mixed: adapter boundaries are clear at API/TUI edges but leaky in CLI command internals.

## Violations

### Violation 1: CLI migration command embeds config migration workflow logic

- **File:** `services/rentl-cli/src/rentl/main.py:3712`
- **Severity:** High
- **Evidence:**
  ```python
  @app.command()
  def migrate(
      config_path: Path = CONFIG_OPTION,
      dry_run: bool = typer.Option(
          False, "--dry-run", help="Show what would change without writing"
      ),
  ) -> None:
      """Migrate rentl.toml config file to the current schema version.
  ...
      # Plan migrations
      registry = get_registry()
      migration_steps = plan_migrations(current_version, target_version, registry)
  ...
      if dry_run:
          return
  
      # Apply migrations
      migrated_config = apply_migrations(config_data, migration_steps, registry)
  ...
      backup_path = config_path.with_suffix(".toml.bak")
      backup_path.write_bytes(config_path.read_bytes())
      migrated_toml = _dict_to_toml(migrated_config)
      config_path.write_text(migrated_toml, encoding="utf-8")
  ```
- **Recommendation:** Move migration lifecycle orchestration into a core service method (e.g., `MigrationService.run(...)`) that returns a typed result model. CLI should pass inputs (path, dry_run), render human output, and never perform migration state machine logic itself.

### Violation 2: CLI `check-secrets` command performs security validation logic in surface layer

- **File:** `services/rentl-cli/src/rentl/main.py:3574`
- **Severity:** High
- **Evidence:**
  ```python
  @app.command()
  def check_secrets(config_path: Path = CONFIG_OPTION) -> None:
      ...
      # Load TOML config
      try:
          with config_path.open("rb") as config_file:
              config_data = tomllib.load(config_file)
      except Exception as exc:
          raise typer.Exit(code=ExitCode.VALIDATION_ERROR.value) from None

      # Check endpoint.api_key_env
      if "endpoint" in config_data:
          api_key_env = config_data["endpoint"].get("api_key_env", "")
          if api_key_env and _looks_like_secret(api_key_env):
              findings.append(...)
  ...
      # Check .env files in project directory
      project_dir = config_path.parent
      env_file = project_dir / ".env"
      if env_file.exists():
          is_git_repo = False
          try:
              git_check = subprocess.run(["git", "rev-parse", "--git-dir"], ...)
  ```
- **Recommendation:** Extract secret-audit rules into core validation component and return structured findings. Keep CLI concerns to option parsing and presentation only; avoid ad hoc security heuristics in command handlers.

### Violation 3: CLI reimplements TOML serialization helpers instead of reusing core/domain utilities

- **File:** `services/rentl-cli/src/rentl/main.py:3910`
- **Severity:** Medium
- **Evidence:**
  ```python
  def _dict_to_toml(data: dict) -> str:
      """Convert a dictionary to TOML format string.
      ...
      def _write_value(value: object) -> str:
          if isinstance(value, bool):
              return "true" if value else "false"
          elif isinstance(value, int | float):
              return str(value)
          elif isinstance(value, str):
              # Escape quotes and backslashes
              escaped = value.replace("\\", "\\\\").replace('"', '\\"')
              return f'"{escaped}"'
          elif isinstance(value, list):
              items = [_write_value(item) for item in value]
              return f"[{', '.join(items)}]"
  ```
- **Recommendation:** Use a shared IO/config serializer in core (or `rentl-io`) for TOML output instead of duplicating serialization logic in CLI.

## Compliant Examples

- `services/rentl-api/src/rentl_api/main.py:1` — exposes FastAPI app and health endpoint wrapper with no domain logic.
- `services/rentl-tui/src/rentl_tui/app.py:1` — minimal app composition and run call, with no business orchestration.
- `services/rentl-cli/src/rentl/main.py:258` — help command delegates phase/command content to `get_command_help` and focuses on presentation.

## Scoring Rationale

- **Coverage:** About 2 of 3 surface layers are thin; `rentl-cli` contains several non-trivial business-rule functions and command orchestration paths that should be in core.
- **Severity:** High-severity violations are present because migration and secret-validation flows are core-domain concerns and can be used by non-CLI workflows.
- **Trend:** API and TUI are clean and small, while legacy CLI command internals remain more monolithic and procedural, indicating architectural inconsistency.
- **Risk:** Medium-to-high operational risk from duplicated logic (validation and transformation), inconsistent behavior across surfaces, and harder testability when adapting new surfaces in future.
