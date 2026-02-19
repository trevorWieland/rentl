"""BDD integration tests for migrate CLI command."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_schemas.config import RunConfig

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/migrate.feature")


class MigrateContext:
    """Context object for migrate BDD scenarios."""

    result: Result | None = None
    stdout: str = ""
    config_dir: Path | None = None
    config_path: Path | None = None
    original_version: str = ""


@given("a config file with an old schema version", target_fixture="ctx")
def given_old_config(tmp_path: Path) -> MigrateContext:
    """Create a config file with old schema version 0.0.1.

    Returns:
        MigrateContext with config directory and path.
    """
    ctx = MigrateContext()
    ctx.config_dir = tmp_path
    ctx.config_path = tmp_path / "rentl.toml"
    ctx.original_version = "0.0.1"

    # Write a config with old schema version including all required RunConfig fields
    config_content = """[project]
schema_version = { major = 0, minor = 0, patch = 1 }
project_name = "test-project"

[project.paths]
workspace_dir = "."
input_path = "./input/test.jsonl"
output_dir = "./out"
logs_dir = "./logs"

[project.formats]
input_format = "jsonl"
output_format = "jsonl"

[project.languages]
source_language = "ja"
target_languages = ["en"]

[logging]
sinks = [
    { type = "console" },
]

[endpoint]
provider_name = "test"
base_url = "http://localhost"
api_key_env = "TEST_API_KEY"
model_id = "test-model"

[pipeline.default_model]
model_id = "test-model"

[[pipeline.phases]]
phase = "ingest"

[[pipeline.phases]]
phase = "export"

[concurrency]
max_parallel_requests = 1
max_parallel_scenes = 1

[retry]
max_retries = 1
backoff_s = 1.0
max_backoff_s = 2.0

[cache]
enabled = false
"""
    ctx.config_path.write_text(config_content, encoding="utf-8")
    return ctx


@given("a config file with the current schema version", target_fixture="ctx")
def given_current_config(tmp_path: Path) -> MigrateContext:
    """Create a config file with current schema version.

    Returns:
        MigrateContext with config directory and path.
    """
    ctx = MigrateContext()
    ctx.config_dir = tmp_path
    ctx.config_path = tmp_path / "rentl.toml"
    ctx.original_version = "0.1.0"

    # Write a config with current schema version including all required RunConfig fields
    config_content = """[project]
schema_version = { major = 0, minor = 1, patch = 0 }
project_name = "test-project"

[project.paths]
workspace_dir = "."
input_path = "./input/test.jsonl"
output_dir = "./out"
logs_dir = "./logs"

[project.formats]
input_format = "jsonl"
output_format = "jsonl"

[project.languages]
source_language = "ja"
target_languages = ["en"]

[logging]
sinks = [
    { type = "console" },
]

[endpoint]
provider_name = "test"
base_url = "http://localhost"
api_key_env = "TEST_API_KEY"
model_id = "test-model"

[pipeline.default_model]
model_id = "test-model"

[[pipeline.phases]]
phase = "ingest"

[[pipeline.phases]]
phase = "export"

[concurrency]
max_parallel_requests = 1
max_parallel_scenes = 1

[retry]
max_retries = 1
backoff_s = 1.0
max_backoff_s = 2.0

[cache]
enabled = false
"""
    ctx.config_path.write_text(config_content, encoding="utf-8")
    return ctx


@when("I run the migrate command")
def when_run_migrate(ctx: MigrateContext, cli_runner: CliRunner) -> None:
    """Run the migrate CLI command.

    Args:
        ctx: Migrate context with config path.
        cli_runner: CLI test runner.
    """
    assert ctx.config_path is not None
    ctx.result = cli_runner.invoke(
        cli_main.app, ["migrate", "--config", str(ctx.config_path)]
    )
    ctx.stdout = ctx.result.stdout


@when("I run the migrate command with dry-run")
def when_run_migrate_dry_run(ctx: MigrateContext, cli_runner: CliRunner) -> None:
    """Run the migrate CLI command with --dry-run flag.

    Args:
        ctx: Migrate context with config path.
        cli_runner: CLI test runner.
    """
    assert ctx.config_path is not None
    ctx.result = cli_runner.invoke(
        cli_main.app, ["migrate", "--config", str(ctx.config_path), "--dry-run"]
    )
    ctx.stdout = ctx.result.stdout


@then("the config file is migrated to the current version")
def then_config_migrated(ctx: MigrateContext) -> None:
    """Assert the config file was migrated to current version."""
    assert ctx.config_path is not None
    assert ctx.config_path.exists()

    # Parse and validate the migrated config
    with ctx.config_path.open("rb") as f:
        migrated_dict = tomllib.load(f)
    config = RunConfig.model_validate(migrated_dict)

    # Check schema version was updated
    assert config.project.schema_version.major == 0
    assert config.project.schema_version.minor == 1
    assert config.project.schema_version.patch == 0


@then("a backup file is created")
def then_backup_created(ctx: MigrateContext) -> None:
    """Assert a backup file was created."""
    assert ctx.config_path is not None
    backup_path = ctx.config_path.with_suffix(".toml.bak")
    assert backup_path.exists()

    # Verify backup contains original version
    with backup_path.open("rb") as f:
        backup_dict = tomllib.load(f)

    schema_version = backup_dict["project"]["schema_version"]
    version_str = (
        f"{schema_version['major']}.{schema_version['minor']}.{schema_version['patch']}"
    )
    assert version_str == ctx.original_version


@then("the output shows the migration plan")
def then_output_shows_plan(ctx: MigrateContext) -> None:
    """Assert the output shows migration plan details."""
    assert "migration" in ctx.stdout.lower()
    # Should show version progression
    assert "0.0.1" in ctx.stdout or "0.1.0" in ctx.stdout


@then("the config file is unchanged")
def then_config_unchanged(ctx: MigrateContext) -> None:
    """Assert the config file was not modified."""
    assert ctx.config_path is not None
    assert ctx.config_path.exists()

    # Parse and validate the config
    with ctx.config_path.open("rb") as f:
        config_dict = tomllib.load(f)
    config = RunConfig.model_validate(config_dict)

    # Check schema version is still original
    version_str = str(config.project.schema_version)
    assert version_str == ctx.original_version


@then("no backup file is created")
def then_no_backup_created(ctx: MigrateContext) -> None:
    """Assert no backup file was created."""
    assert ctx.config_path is not None
    backup_path = ctx.config_path.with_suffix(".toml.bak")
    assert not backup_path.exists()


@then("the output indicates the config is already up to date")
def then_output_shows_up_to_date(ctx: MigrateContext) -> None:
    """Assert the output indicates config is already up to date."""
    assert (
        "already up to date" in ctx.stdout.lower() or "up to date" in ctx.stdout.lower()
    )


@when("I load the config via run command")
def when_load_config_via_run(ctx: MigrateContext, cli_runner: CliRunner) -> None:
    """Attempt to load config via validate-connection (fails validation).

    Args:
        ctx: Migrate context with config path.
        cli_runner: CLI test runner.
    """
    assert ctx.config_path is not None
    # Use "validate-connection" which loads the config
    # It will fail validation, but we only care about auto-migration
    ctx.result = cli_runner.invoke(
        cli_main.app, ["validate-connection", "--config", str(ctx.config_path)]
    )
    ctx.stdout = ctx.result.stdout


@then("the config is auto-migrated before validation")
def then_config_auto_migrated(ctx: MigrateContext) -> None:
    """Assert the config file was auto-migrated."""
    assert ctx.config_path is not None
    assert ctx.config_path.exists()

    # Parse and validate the migrated config
    with ctx.config_path.open("rb") as f:
        migrated_dict = tomllib.load(f)
    config = RunConfig.model_validate(migrated_dict)

    # Check schema version was updated
    assert config.project.schema_version.major == 0
    assert config.project.schema_version.minor == 1
    assert config.project.schema_version.patch == 0


@then("the output shows auto-migration occurred")
def then_output_shows_auto_migration(ctx: MigrateContext) -> None:
    """Assert the output shows auto-migration occurred."""
    assert (
        "auto-migrating" in ctx.stdout.lower()
        or "migration complete" in ctx.stdout.lower()
    )
