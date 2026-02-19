"""Unit tests for rentl_core.doctor diagnostic checks."""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import rentl.main as cli_main
from rentl_core.doctor import (
    CheckStatus,
    check_api_keys,
    check_config_file,
    check_config_valid,
    check_llm_connectivity,
    check_python_version,
    check_workspace_dirs,
    run_doctor,
)
from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_schemas.config import (
    CacheConfig,
    ConcurrencyConfig,
    EndpointSetConfig,
    FormatConfig,
    LanguageConfig,
    LoggingConfig,
    LogSinkConfig,
    ModelEndpointConfig,
    ModelSettings,
    PhaseConfig,
    PipelineConfig,
    ProjectConfig,
    ProjectPaths,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.exit_codes import ExitCode
from rentl_schemas.llm import (
    LlmConnectionReport,
    LlmConnectionResult,
    LlmConnectionStatus,
)
from rentl_schemas.primitives import FileFormat, LogSinkType, PhaseName
from rentl_schemas.version import VersionInfo

# Valid test config TOML for testing
VALID_TEST_CONFIG_TOML = """
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


@pytest.fixture
def mock_config(tmp_path: Path) -> RunConfig:
    """Create a minimal valid RunConfig for testing.

    Uses relative paths (like production config) to test path resolution.
    Creates physical directories in tmp_path for tests that check existence.

    Returns:
        RunConfig: Test configuration with temporary workspace.
    """
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    output_dir = workspace_dir / "out"
    output_dir.mkdir()
    logs_dir = workspace_dir / "logs"
    logs_dir.mkdir()

    # Use relative paths like production config
    return RunConfig(
        project=ProjectConfig(
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            project_name="test_project",
            paths=ProjectPaths(
                workspace_dir="workspace",
                input_path="workspace/input.jsonl",
                output_dir="workspace/out",
                logs_dir="workspace/logs",
            ),
            formats=FormatConfig(
                input_format=FileFormat.JSONL,
                output_format=FileFormat.JSONL,
            ),
            languages=LanguageConfig(source_language="ja", target_languages=["en"]),
        ),
        logging=LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.CONSOLE)]),
        endpoint=ModelEndpointConfig(
            provider_name="test_provider",
            base_url="https://api.test.com",
            api_key_env="TEST_API_KEY",
        ),
        pipeline=PipelineConfig(
            phases=[
                PhaseConfig(phase=PhaseName.INGEST),
                PhaseConfig(phase=PhaseName.CONTEXT, agents=["scene_summarizer"]),
                PhaseConfig(phase=PhaseName.PRETRANSLATION, agents=["idiom_labeler"]),
                PhaseConfig(phase=PhaseName.TRANSLATE, agents=["direct_translator"]),
                PhaseConfig(phase=PhaseName.QA, agents=["style_guide_critic"]),
                PhaseConfig(phase=PhaseName.EDIT, agents=["basic_editor"]),
                PhaseConfig(phase=PhaseName.EXPORT),
            ],
            default_model=ModelSettings(model_id="test/model"),
        ),
        concurrency=ConcurrencyConfig(max_parallel_requests=8, max_parallel_scenes=4),
        retry=RetryConfig(max_retries=3, backoff_s=1.0, max_backoff_s=30.0),
        cache=CacheConfig(enabled=False),
    )


class TestCheckPythonVersion:
    """Tests for check_python_version."""

    def test_python_version_pass(self) -> None:
        """Test that current Python version passes (must be >= 3.11)."""
        result = check_python_version()
        assert result.name == "Python Version"
        # Current Python is 3.14, so it should pass
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None
        assert "3.11" in result.message

    def test_python_version_fail(self) -> None:
        """Test that old Python version fails."""
        with patch.object(sys, "version_info") as mock_version:
            mock_version.major = 3
            mock_version.minor = 10
            mock_version.micro = 0
            result = check_python_version()
            assert result.status == CheckStatus.FAIL
            assert "3.10.0" in result.message
            assert result.fix_suggestion is not None
            assert "3.11" in result.fix_suggestion


class TestCheckConfigFile:
    """Tests for check_config_file."""

    def test_config_file_exists(self, tmp_path: Path) -> None:
        """Test that existing config file passes."""
        config_path = tmp_path / "rentl.toml"
        config_path.write_text("[project]\n")

        result = check_config_file(config_path)
        assert result.status == CheckStatus.PASS
        assert str(config_path) in result.message
        assert result.fix_suggestion is None

    def test_config_file_missing(self, tmp_path: Path) -> None:
        """Test that missing config file fails."""
        config_path = tmp_path / "rentl.toml"

        result = check_config_file(config_path)
        assert result.status == CheckStatus.FAIL
        assert "not found" in result.message
        assert result.fix_suggestion is not None
        assert "rentl init" in result.fix_suggestion

    def test_config_file_is_directory(self, tmp_path: Path) -> None:
        """Test that directory at config path fails."""
        config_path = tmp_path / "rentl.toml"
        config_path.mkdir()

        result = check_config_file(config_path)
        assert result.status == CheckStatus.FAIL
        assert "not a file" in result.message
        assert result.fix_suggestion is not None


class TestCheckConfigValid:
    """Tests for check_config_valid."""

    def test_config_valid_pass(self, tmp_path: Path) -> None:
        """Test that valid config passes."""
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(VALID_TEST_CONFIG_TOML)

        result = check_config_valid(config_path)
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None

    def test_config_toml_syntax_error(self, tmp_path: Path) -> None:
        """Test that invalid TOML syntax fails."""
        config_path = tmp_path / "rentl.toml"
        config_path.write_text("[project\n")  # Missing closing bracket

        result = check_config_valid(config_path)
        assert result.status == CheckStatus.FAIL
        assert "TOML syntax error" in result.message
        assert result.fix_suggestion is not None

    def test_config_validation_error(self, tmp_path: Path) -> None:
        """Test that schema validation error fails."""
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(
            """
[project]
project_name = "test"
# Missing schema_version, paths, etc.
"""
        )

        result = check_config_valid(config_path)
        assert result.status == CheckStatus.FAIL
        assert "validation error" in result.message
        assert result.fix_suggestion is not None

    def test_config_missing_file(self, tmp_path: Path) -> None:
        """Test that missing file reports dependency failure."""
        config_path = tmp_path / "rentl.toml"

        result = check_config_valid(config_path)
        assert result.status == CheckStatus.FAIL
        assert "does not exist" in result.message
        assert result.fix_suggestion is not None
        assert "Config File" in result.fix_suggestion

    def test_config_auto_migrates_outdated_schema(self, tmp_path: Path) -> None:
        """Test that outdated config is auto-migrated before validation."""
        config_path = tmp_path / "rentl.toml"
        # Create config with old schema version 0.0.1
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

        # Run check_config_valid which should auto-migrate
        result = check_config_valid(config_path)
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None

        # Verify backup was created
        backup_path = config_path.with_suffix(".toml.bak")
        assert backup_path.exists()

        # Verify migrated config has updated schema version — validate with schema
        with open(config_path, "rb") as f:
            migrated_data = tomllib.load(f)

        migrated_config = RunConfig.model_validate(migrated_data)
        assert migrated_config.project.schema_version.major == 0
        assert migrated_config.project.schema_version.minor == 1
        assert migrated_config.project.schema_version.patch == 0


class TestCheckWorkspaceDirs:
    """Tests for check_workspace_dirs."""

    def test_all_dirs_exist(self, mock_config: RunConfig, tmp_path: Path) -> None:
        """Test that all existing directories pass."""
        result = check_workspace_dirs(mock_config, tmp_path)
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None

    def test_missing_output_dir(self, mock_config: RunConfig, tmp_path: Path) -> None:
        """Test that missing output directory fails."""
        # Resolve relative path from config using config_dir
        output_dir = tmp_path / mock_config.project.paths.output_dir
        output_dir.rmdir()

        result = check_workspace_dirs(mock_config, tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "output" in result.message
        assert result.fix_suggestion is not None
        assert "mkdir" in result.fix_suggestion

    def test_missing_multiple_dirs(
        self, mock_config: RunConfig, tmp_path: Path
    ) -> None:
        """Test that multiple missing directories are reported."""
        # Resolve relative paths from config using config_dir
        output_dir = tmp_path / mock_config.project.paths.output_dir
        logs_dir = tmp_path / mock_config.project.paths.logs_dir
        output_dir.rmdir()
        logs_dir.rmdir()

        result = check_workspace_dirs(mock_config, tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "output" in result.message
        assert "logs" in result.message

    def test_paths_resolve_relative_to_config_dir_not_cwd(
        self, mock_config: RunConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that workspace paths resolve relative to config_dir, not CWD.

        Regression test for audit round 1 signpost: paths were incorrectly
        resolved relative to CWD, causing false PASSes when unrelated CWD
        directories happened to exist.
        """
        # Change CWD to a different directory with its own "workspace/out/logs"
        unrelated_dir = tmp_path / "unrelated_cwd"
        unrelated_dir.mkdir()
        (unrelated_dir / "workspace").mkdir()
        (unrelated_dir / "workspace" / "out").mkdir()
        (unrelated_dir / "workspace" / "logs").mkdir()
        monkeypatch.chdir(unrelated_dir)

        # Delete the actual workspace directories (relative to config_dir, not CWD)
        actual_output = tmp_path / mock_config.project.paths.output_dir
        actual_logs = tmp_path / mock_config.project.paths.logs_dir
        actual_output.rmdir()
        actual_logs.rmdir()

        # Check should FAIL because config_dir paths are missing,
        # even though CWD has "workspace/out/logs"
        result = check_workspace_dirs(mock_config, tmp_path)
        assert result.status == CheckStatus.FAIL
        assert "output" in result.message
        assert "logs" in result.message


class TestCheckApiKeys:
    """Tests for check_api_keys."""

    def test_all_api_keys_present(
        self, mock_config: RunConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that all present API keys pass."""
        monkeypatch.setenv("TEST_API_KEY", "test_value")

        result = check_api_keys(mock_config)
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None
        assert "1" in result.message

    def test_missing_api_key(
        self, mock_config: RunConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing API key fails."""
        monkeypatch.delenv("TEST_API_KEY", raising=False)

        result = check_api_keys(mock_config)
        assert result.status == CheckStatus.FAIL
        assert "TEST_API_KEY" in result.message
        assert result.fix_suggestion is not None
        assert ".env" in result.fix_suggestion

    def test_api_key_from_dotenv_simulation(
        self, mock_config: RunConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that API keys loaded from .env are visible to doctor checks.

        This simulates the scenario where the CLI layer has already loaded
        .env files via _load_dotenv() before calling run_doctor().
        The actual dotenv loading happens in the CLI layer, but this test
        verifies that once loaded, the keys are visible to the checks.
        """
        # Clear env first
        monkeypatch.delenv("TEST_API_KEY", raising=False)

        # Simulate what happens after _load_dotenv() loads .env
        monkeypatch.setenv("TEST_API_KEY", "key_from_dotenv")

        # Verify the check can see the key
        result = check_api_keys(mock_config)
        assert result.status == CheckStatus.PASS
        assert result.fix_suggestion is None

    def test_api_key_dotenv_local_override_simulation(
        self, mock_config: RunConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that .env.local values are visible to doctor checks.

        This simulates the scenario where both .env and .env.local exist.
        The actual dotenv loading happens in the CLI layer, but this test
        documents that the checks see whichever value was loaded last.
        """
        # Simulate .env.local having been loaded
        monkeypatch.setenv("TEST_API_KEY", "key_from_env_local")

        result = check_api_keys(mock_config)
        assert result.status == CheckStatus.PASS
        assert "1" in result.message

    def test_multi_endpoint_config(
        self, mock_config: RunConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test multi-endpoint config with mixed key presence."""
        mock_config = mock_config.model_copy(
            update={
                "endpoint": None,
                "endpoints": EndpointSetConfig(
                    default="provider1",
                    endpoints=[
                        ModelEndpointConfig(
                            provider_name="provider1",
                            base_url="https://api1.test.com",
                            api_key_env="PROVIDER1_KEY",
                        ),
                        ModelEndpointConfig(
                            provider_name="provider2",
                            base_url="https://api2.test.com",
                            api_key_env="PROVIDER2_KEY",
                        ),
                    ],
                ),
            }
        )

        monkeypatch.setenv("PROVIDER1_KEY", "value1")
        monkeypatch.delenv("PROVIDER2_KEY", raising=False)

        result = check_api_keys(mock_config)
        assert result.status == CheckStatus.FAIL
        assert "PROVIDER2_KEY" in result.message
        assert "PROVIDER1_KEY" not in result.message


class TestCheckLlmConnectivity:
    """Tests for check_llm_connectivity."""

    @pytest.mark.asyncio
    async def test_all_connections_succeed(
        self, mock_config: RunConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that all successful connections pass."""
        monkeypatch.setenv("TEST_API_KEY", "test_value")

        mock_runtime = AsyncMock(spec=LlmRuntimeProtocol)
        mock_report = LlmConnectionReport(
            results=[
                LlmConnectionResult(
                    endpoint_ref=None,
                    provider_name="test_provider",
                    base_url="https://api.test.com",
                    api_key_env="TEST_API_KEY",
                    model_id="test/model",
                    phases=None,
                    status=LlmConnectionStatus.SUCCESS,
                    attempts=1,
                    duration_ms=100,
                    response_text="OK",
                    error_message=None,
                )
            ],
            success_count=1,
            failure_count=0,
            skipped_count=0,
        )

        with (
            patch("rentl_core.doctor.build_connection_plan") as mock_plan,
            patch("rentl_core.doctor.validate_connections", return_value=mock_report),
        ):
            mock_plan.return_value = ([MagicMock()], [])

            result = await check_llm_connectivity(mock_runtime, mock_config)
            assert result.status == CheckStatus.PASS
            assert "1 endpoint(s) reachable" in result.message
            assert result.fix_suggestion is None

    @pytest.mark.asyncio
    async def test_connection_failures(
        self, mock_config: RunConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that connection failures are reported."""
        monkeypatch.setenv("TEST_API_KEY", "test_value")

        mock_runtime = AsyncMock(spec=LlmRuntimeProtocol)
        mock_report = LlmConnectionReport(
            results=[
                LlmConnectionResult(
                    endpoint_ref=None,
                    provider_name="test_provider",
                    base_url="https://api.test.com",
                    api_key_env="TEST_API_KEY",
                    model_id="test/model",
                    phases=None,
                    status=LlmConnectionStatus.FAILED,
                    attempts=3,
                    duration_ms=500,
                    response_text=None,
                    error_message="Connection timeout",
                )
            ],
            success_count=0,
            failure_count=1,
            skipped_count=0,
        )

        with (
            patch("rentl_core.doctor.build_connection_plan") as mock_plan,
            patch("rentl_core.doctor.validate_connections", return_value=mock_report),
        ):
            mock_plan.return_value = ([MagicMock()], [])

            result = await check_llm_connectivity(mock_runtime, mock_config)
            assert result.status == CheckStatus.FAIL
            assert "1/1 endpoint(s) failed" in result.message
            assert "test_provider" in result.message
            assert result.fix_suggestion is not None
            assert "validate-connection" in result.fix_suggestion

    @pytest.mark.asyncio
    async def test_no_llm_phases_configured(self, mock_config: RunConfig) -> None:
        """Test warning when no LLM phases are configured."""
        mock_runtime = AsyncMock(spec=LlmRuntimeProtocol)

        with patch("rentl_core.doctor.build_connection_plan") as mock_plan:
            mock_plan.return_value = ([], [])

            result = await check_llm_connectivity(mock_runtime, mock_config)
            assert result.status == CheckStatus.WARN
            assert "No LLM phases configured" in result.message
            assert result.fix_suggestion is not None

    @pytest.mark.asyncio
    async def test_all_endpoints_skipped(self, mock_config: RunConfig) -> None:
        """Test warning when all endpoints are skipped."""
        mock_runtime = AsyncMock(spec=LlmRuntimeProtocol)
        mock_report = LlmConnectionReport(
            results=[
                LlmConnectionResult(
                    endpoint_ref=None,
                    provider_name="test_provider",
                    base_url="https://api.test.com",
                    api_key_env="TEST_API_KEY",
                    model_id=None,
                    phases=None,
                    status=LlmConnectionStatus.SKIPPED,
                    attempts=0,
                    duration_ms=None,
                    response_text=None,
                    error_message="No model configured",
                )
            ],
            success_count=0,
            failure_count=0,
            skipped_count=1,
        )

        with (
            patch("rentl_core.doctor.build_connection_plan") as mock_plan,
            patch("rentl_core.doctor.validate_connections", return_value=mock_report),
        ):
            mock_plan.return_value = ([MagicMock()], [])

            result = await check_llm_connectivity(mock_runtime, mock_config)
            assert result.status == CheckStatus.WARN
            assert "skipped" in result.message
            assert result.fix_suggestion is not None


class TestRunDoctor:
    """Tests for run_doctor orchestration."""

    @pytest.mark.asyncio
    async def test_all_checks_pass(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that all passing checks result in overall pass."""
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(VALID_TEST_CONFIG_TOML)

        # Create workspace directories
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        monkeypatch.setenv("TEST_KEY", "test_value")

        mock_runtime = AsyncMock(spec=LlmRuntimeProtocol)
        mock_report = LlmConnectionReport(
            results=[],
            success_count=1,
            failure_count=0,
            skipped_count=0,
        )

        with (
            patch("rentl_core.doctor.build_connection_plan") as mock_plan,
            patch("rentl_core.doctor.validate_connections", return_value=mock_report),
        ):
            mock_plan.return_value = ([MagicMock()], [])

            report = await run_doctor(config_path, runtime=mock_runtime)
            assert report.overall_status == CheckStatus.PASS
            assert report.exit_code == ExitCode.SUCCESS
            assert len(report.checks) == 6

    @pytest.mark.asyncio
    async def test_config_failure_cascades(self, tmp_path: Path) -> None:
        """Test that config failure cascades to dependent checks."""
        config_path = tmp_path / "rentl.toml"
        # No config file exists

        report = await run_doctor(config_path)
        assert report.overall_status == CheckStatus.FAIL
        assert report.exit_code == ExitCode.CONFIG_ERROR

        # Check names
        check_names = [check.name for check in report.checks]
        assert "Config File" in check_names
        assert "Workspace Directories" in check_names
        assert "API Keys" in check_names

        # Dependent checks should fail with cascade message
        workspace_check = next(
            c for c in report.checks if c.name == "Workspace Directories"
        )
        assert workspace_check.status == CheckStatus.FAIL
        assert "config invalid" in workspace_check.message

    @pytest.mark.asyncio
    async def test_warnings_result_in_warn_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that warnings result in overall warn status with success exit code."""
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(VALID_TEST_CONFIG_TOML)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        monkeypatch.setenv("TEST_KEY", "test_value")

        # No runtime provided - will result in warning
        report = await run_doctor(config_path, runtime=None)
        assert report.overall_status == CheckStatus.WARN
        assert report.exit_code == ExitCode.SUCCESS

        llm_check = next(c for c in report.checks if c.name == "LLM Connectivity")
        assert llm_check.status == CheckStatus.WARN
        assert "skipped" in llm_check.message

    @pytest.mark.asyncio
    async def test_no_runtime_skips_connectivity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing runtime skips connectivity check."""
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(VALID_TEST_CONFIG_TOML)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        monkeypatch.setenv("TEST_KEY", "test_value")

        report = await run_doctor(config_path, runtime=None)

        llm_check = next(c for c in report.checks if c.name == "LLM Connectivity")
        assert llm_check.status == CheckStatus.WARN
        assert "skipped" in llm_check.message
        assert "no runtime provided" in llm_check.message

    @pytest.mark.asyncio
    async def test_dotenv_loaded_keys_visible_to_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that API keys loaded from .env are visible to doctor checks.

        This test simulates the doctor workflow where the CLI layer loads
        .env files from the config directory before calling run_doctor().
        The actual dotenv loading happens in the CLI (_load_dotenv), but
        this verifies that once loaded, the keys are visible to all checks.

        This documents the expected integration between CLI dotenv loading
        and core doctor checks for the config directory .env path.
        """
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(VALID_TEST_CONFIG_TOML)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Clear environment
        monkeypatch.delenv("TEST_KEY", raising=False)

        # Simulate CLI layer having loaded .env file from config directory
        # (In real usage, _load_dotenv(config_path) would do this)
        monkeypatch.setenv("TEST_KEY", "value_from_dotenv")

        # Run doctor - it should see the environment variable
        report = await run_doctor(config_path, runtime=None)

        # API key check should pass
        api_check = next(c for c in report.checks if c.name == "API Keys")
        assert api_check.status == CheckStatus.PASS
        assert "1" in api_check.message

    @pytest.mark.asyncio
    async def test_dotenv_local_values_visible_to_checks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that .env and .env.local files are loaded in doctor context.

        This test verifies the actual dotenv loading behavior in the doctor
        context: both .env and .env.local are loaded, and .env takes precedence
        when both define the same key (both loaded with override=False, first wins).

        This exercises real file loading rather than just monkeypatch.setenv.
        """
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(VALID_TEST_CONFIG_TOML)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Create .env file with TEST_KEY
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_KEY=value_from_env\nENV_ONLY=env_value\n")

        # Create .env.local file with TEST_KEY and a local-only key
        env_local_file = tmp_path / ".env.local"
        env_local_file.write_text("TEST_KEY=value_from_local\nLOCAL_ONLY=local_value\n")

        # Clear environment
        monkeypatch.delenv("TEST_KEY", raising=False)
        monkeypatch.delenv("ENV_ONLY", raising=False)
        monkeypatch.delenv("LOCAL_ONLY", raising=False)

        # Load dotenv files (as CLI layer does)
        cli_main._load_dotenv(config_path)

        # Run doctor
        report = await run_doctor(config_path, runtime=None)

        # API key check should pass
        api_check = next(c for c in report.checks if c.name == "API Keys")
        assert api_check.status == CheckStatus.PASS

        # Verify precedence: .env wins for shared keys
        assert os.getenv("TEST_KEY") == "value_from_env"
        # Verify both files are loaded
        assert os.getenv("ENV_ONLY") == "env_value"
        assert os.getenv("LOCAL_ONLY") == "local_value"

    @pytest.mark.asyncio
    async def test_api_key_failure_takes_precedence_over_connectivity_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that config errors take precedence over connection errors.

        Regression test for signpost 3: when both API Keys and LLM Connectivity
        fail, exit code should be CONFIG_ERROR (not CONNECTION_ERROR).
        """
        config_path = tmp_path / "rentl.toml"
        config_path.write_text(VALID_TEST_CONFIG_TOML)

        out_dir = tmp_path / "out"
        out_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        # Unset the required API key
        monkeypatch.delenv("TEST_KEY", raising=False)

        # Mock failed connectivity
        mock_runtime = AsyncMock(spec=LlmRuntimeProtocol)
        mock_report = LlmConnectionReport(
            results=[
                LlmConnectionResult(
                    provider_name="test",
                    base_url="https://test.example.com",
                    api_key_env="TEST_KEY",
                    status=LlmConnectionStatus.FAILED,
                    attempts=1,
                    error_message="Connection failed",
                )
            ],
            success_count=0,
            failure_count=1,
            skipped_count=0,
        )

        with (
            patch("rentl_core.doctor.build_connection_plan") as mock_plan,
            patch("rentl_core.doctor.validate_connections", return_value=mock_report),
        ):
            mock_plan.return_value = ([MagicMock()], [])

            report = await run_doctor(config_path, runtime=mock_runtime)

            # Both checks should fail
            api_check = next(c for c in report.checks if c.name == "API Keys")
            assert api_check.status == CheckStatus.FAIL
            assert "TEST_KEY" in api_check.message

            llm_check = next(c for c in report.checks if c.name == "LLM Connectivity")
            assert llm_check.status == CheckStatus.FAIL

            # Exit code should be CONFIG_ERROR (config check failed)
            # not CONNECTION_ERROR (even though connectivity also failed)
            assert report.overall_status == CheckStatus.FAIL
            assert report.exit_code == ExitCode.CONFIG_ERROR
