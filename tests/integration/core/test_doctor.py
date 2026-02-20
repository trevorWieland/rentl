"""BDD integration tests for doctor auto-migration functionality.

These tests verify that the doctor module correctly auto-migrates
outdated config files before validation.
"""

import tomllib
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from rentl_core.doctor import CheckResult, CheckStatus, check_config_valid
from rentl_schemas.config import RunConfig

# Link feature file
scenarios("../features/core/doctor.feature")

_OLD_CONFIG = """
[project]
schema_version = { major = 0, minor = 0, patch = 1 }
project_name = "test"

[project.paths]
workspace_dir = "."
input_path = "./input.jsonl"
output_dir = "./out"
logs_dir = "./logs"

[project.formats]
input_format = "jsonl"
output_format = "jsonl"

[project.languages]
source_language = "ja"
target_languages = ["en"]

[logging]
sinks = [{ type = "console" }]

[endpoint]
provider_name = "test"
base_url = "https://api.test.com"
api_key_env = "TEST_KEY"

[pipeline]

[pipeline.default_model]
model_id = "test/model"

[[pipeline.phases]]
phase = "ingest"

[[pipeline.phases]]
phase = "context"
agents = ["scene_summarizer"]

[[pipeline.phases]]
phase = "pretranslation"
agents = ["idiom_labeler"]

[[pipeline.phases]]
phase = "translate"
agents = ["direct_translator"]

[[pipeline.phases]]
phase = "qa"
agents = ["style_guide_critic"]

[[pipeline.phases]]
phase = "edit"
agents = ["basic_editor"]

[[pipeline.phases]]
phase = "export"

[concurrency]
max_parallel_requests = 8
max_parallel_scenes = 4

[retry]
max_retries = 3
backoff_s = 1.0
max_backoff_s = 30.0

[cache]
enabled = false
"""

_CURRENT_CONFIG = """
[project]
schema_version = { major = 0, minor = 1, patch = 0 }
project_name = "test"

[project.paths]
workspace_dir = "."
input_path = "./input.jsonl"
output_dir = "./out"
logs_dir = "./logs"

[project.formats]
input_format = "jsonl"
output_format = "jsonl"

[project.languages]
source_language = "ja"
target_languages = ["en"]

[logging]
sinks = [{ type = "console" }]

[endpoint]
provider_name = "test"
base_url = "https://api.test.com"
api_key_env = "TEST_KEY"

[pipeline]

[pipeline.default_model]
model_id = "test/model"

[[pipeline.phases]]
phase = "ingest"

[[pipeline.phases]]
phase = "context"
agents = ["scene_summarizer"]

[[pipeline.phases]]
phase = "pretranslation"
agents = ["idiom_labeler"]

[[pipeline.phases]]
phase = "translate"
agents = ["direct_translator"]

[[pipeline.phases]]
phase = "qa"
agents = ["style_guide_critic"]

[[pipeline.phases]]
phase = "edit"
agents = ["basic_editor"]

[[pipeline.phases]]
phase = "export"

[concurrency]
max_parallel_requests = 8
max_parallel_scenes = 4

[retry]
max_retries = 3
backoff_s = 1.0
max_backoff_s = 30.0

[cache]
enabled = false
"""


class DoctorContext:
    """Context object for doctor BDD scenarios."""

    config_path: Path | None = None
    result: CheckResult | None = None


@given("a config file with old schema version 0.0.1", target_fixture="ctx")
def given_old_config(tmp_path: Path) -> DoctorContext:
    """Create a config file with outdated schema version 0.0.1.

    Returns:
        DoctorContext with fields initialized.
    """
    ctx = DoctorContext()
    ctx.config_path = tmp_path / "rentl.toml"
    ctx.config_path.write_text(_OLD_CONFIG)
    return ctx


@given("a config file with current schema version 0.1.0", target_fixture="ctx")
def given_current_config(tmp_path: Path) -> DoctorContext:
    """Create a config file with current schema version 0.1.0.

    Returns:
        DoctorContext with fields initialized.
    """
    ctx = DoctorContext()
    ctx.config_path = tmp_path / "rentl.toml"
    ctx.config_path.write_text(_CURRENT_CONFIG)
    return ctx


@when("I run check_config_valid")
def when_check_config_valid(ctx: DoctorContext) -> None:
    """Run the check_config_valid doctor check on the config file."""
    assert ctx.config_path is not None
    ctx.result = check_config_valid(ctx.config_path)


@then("the check passes")
def then_check_passes(ctx: DoctorContext) -> None:
    """Assert the doctor check passed with no fix suggestion."""
    assert ctx.result is not None
    assert ctx.result.status == CheckStatus.PASS
    assert ctx.result.fix_suggestion is None


@then("a backup file is created")
def then_backup_created(ctx: DoctorContext) -> None:
    """Assert a .toml.bak backup file was created alongside the config."""
    assert ctx.config_path is not None
    backup_path = ctx.config_path.with_suffix(".toml.bak")
    assert backup_path.exists()


@then("the backup contains the old version")
def then_backup_old_version(ctx: DoctorContext) -> None:
    """Assert the backup file contains the original old schema version."""
    assert ctx.config_path is not None
    backup_path = ctx.config_path.with_suffix(".toml.bak")
    with open(backup_path, "rb") as f:
        backup_data = tomllib.load(f)
    backup_config = RunConfig.model_validate(backup_data)
    assert backup_config.project.schema_version.major == 0
    assert backup_config.project.schema_version.minor == 0
    assert backup_config.project.schema_version.patch == 1


@then("the migrated config has version 0.1.0")
def then_migrated_version(ctx: DoctorContext) -> None:
    """Assert the migrated config file has schema version 0.1.0."""
    assert ctx.config_path is not None
    with open(ctx.config_path, "rb") as f:
        migrated_dict = tomllib.load(f)
    migrated = RunConfig.model_validate(migrated_dict)
    assert migrated.project.schema_version.major == 0
    assert migrated.project.schema_version.minor == 1
    assert migrated.project.schema_version.patch == 0


@then("no backup file is created")
def then_no_backup(ctx: DoctorContext) -> None:
    """Assert no backup file was created when migration is unnecessary."""
    assert ctx.config_path is not None
    backup_path = ctx.config_path.with_suffix(".toml.bak")
    assert not backup_path.exists()


@then("the config version is unchanged")
def then_version_unchanged(ctx: DoctorContext) -> None:
    """Assert the config file retains its original schema version."""
    assert ctx.config_path is not None
    with open(ctx.config_path, "rb") as f:
        config_dict = tomllib.load(f)
    config = RunConfig.model_validate(config_dict)
    assert config.project.schema_version.major == 0
    assert config.project.schema_version.minor == 1
    assert config.project.schema_version.patch == 0
