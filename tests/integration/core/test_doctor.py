"""Integration tests for doctor auto-migration functionality.

These tests verify that the doctor module correctly auto-migrates
outdated config files before validation.
"""

import tomllib
from pathlib import Path

import pytest

from rentl_core.doctor import CheckStatus, check_config_valid

# Apply integration marker
pytestmark = pytest.mark.integration


class TestDoctorAutoMigration:
    """Integration tests for doctor config auto-migration."""

    def test_given_outdated_config_when_checking_validity_then_auto_migrates(
        self, tmp_path: Path
    ) -> None:
        """Given: Config file with old schema version 0.0.1.

        When: Running check_config_valid.
        Then: Config is auto-migrated to 0.1.0, backup created, and validation passes.
        """
        # Given: Config with old schema version 0.0.1
        config_path = tmp_path / "rentl.toml"
        old_config = """
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
        config_path.write_text(old_config)

        # When: Running check_config_valid (which should trigger auto-migration)
        result = check_config_valid(config_path)

        # Then: Check passes
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None

        # And: Backup file was created
        backup_path = config_path.with_suffix(".toml.bak")
        assert backup_path.exists()

        # And: Original backup contains old version
        with open(backup_path, "rb") as f:
            backup_data = tomllib.load(f)
        assert backup_data["project"]["schema_version"]["major"] == 0
        assert backup_data["project"]["schema_version"]["minor"] == 0
        assert backup_data["project"]["schema_version"]["patch"] == 1

        # And: Migrated config has updated schema version
        with open(config_path, "rb") as f:
            migrated_data = tomllib.load(f)
        assert migrated_data["project"]["schema_version"]["major"] == 0
        assert migrated_data["project"]["schema_version"]["minor"] == 1
        assert migrated_data["project"]["schema_version"]["patch"] == 0

    def test_given_current_config_when_checking_validity_then_no_migration(
        self, tmp_path: Path
    ) -> None:
        """Given: Config file with current schema version 0.1.0.

        When: Running check_config_valid.
        Then: No migration occurs and no backup is created.
        """
        # Given: Config with current schema version 0.1.0
        config_path = tmp_path / "rentl.toml"
        current_config = """
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
        config_path.write_text(current_config)

        # When: Running check_config_valid
        result = check_config_valid(config_path)

        # Then: Check passes
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None

        # And: No backup file was created
        backup_path = config_path.with_suffix(".toml.bak")
        assert not backup_path.exists()

        # And: Config version remains unchanged
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
        assert config_data["project"]["schema_version"]["major"] == 0
        assert config_data["project"]["schema_version"]["minor"] == 1
        assert config_data["project"]["schema_version"]["patch"] == 0
