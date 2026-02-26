"""Unit tests for verify-models CLI command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from rentl.main import app
from rentl_core.compatibility import (
    ModelVerificationResult,
    PhaseResult,
    PhaseVerificationStatus,
    RegistryVerificationResult,
)
from rentl_schemas.compatibility import (
    VerifiedModelEntry,
    VerifiedModelRegistry,
)
from rentl_schemas.config import (
    EndpointSetConfig,
    ModelEndpointConfig,
)
from rentl_schemas.primitives import PhaseName


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner.

    Returns:
        CliRunner: Test runner for invoking CLI commands.
    """
    return CliRunner()


def _make_phase_results(*, passed: bool = True) -> list[PhaseResult]:
    """Build a list of phase results for all 5 phases.

    Args:
        passed: Whether all phases should pass.

    Returns:
        list[PhaseResult]: Phase results for each pipeline phase.
    """
    phases = [
        PhaseName.CONTEXT,
        PhaseName.PRETRANSLATION,
        PhaseName.TRANSLATE,
        PhaseName.QA,
        PhaseName.EDIT,
    ]
    return [
        PhaseResult(
            phase=phase,
            status=(
                PhaseVerificationStatus.PASSED
                if passed
                else PhaseVerificationStatus.FAILED
            ),
            error_message=(None if passed else f"{phase} failed: mock error"),
        )
        for phase in phases
    ]


def _make_registry() -> VerifiedModelRegistry:
    """Build a minimal test registry with two models.

    Returns:
        VerifiedModelRegistry: Registry with one local and one
        openrouter model.
    """
    return VerifiedModelRegistry(
        models=[
            VerifiedModelEntry(
                model_id="test/local-model",
                endpoint_type="local",
                endpoint_ref="lm-studio",
                load_endpoint=("http://localhost:1234/api/v1/models/load"),
            ),
            VerifiedModelEntry(
                model_id="test/openrouter-model",
                endpoint_type="openrouter",
                endpoint_ref="openrouter",
            ),
        ]
    )


_LM_STUDIO_EP = ModelEndpointConfig(
    provider_name="lm-studio",
    base_url="http://localhost:1234/v1",
    api_key_env="LM_STUDIO_KEY",
)
_OPENROUTER_EP = ModelEndpointConfig(
    provider_name="openrouter",
    base_url="https://openrouter.ai/api/v1",
    api_key_env="OPENROUTER_KEY",
)


def _make_all_pass_result() -> RegistryVerificationResult:
    """Build a result where all models pass.

    Returns:
        RegistryVerificationResult: All-pass result.
    """
    return RegistryVerificationResult(
        passed=True,
        model_results=[
            ModelVerificationResult(
                model_id="test/local-model",
                passed=True,
                phase_results=_make_phase_results(passed=True),
            ),
            ModelVerificationResult(
                model_id="test/openrouter-model",
                passed=True,
                phase_results=_make_phase_results(passed=True),
            ),
        ],
    )


def _make_partial_fail_result() -> RegistryVerificationResult:
    """Build a result where one model fails.

    Returns:
        RegistryVerificationResult: Partial-fail result.
    """
    return RegistryVerificationResult(
        passed=False,
        model_results=[
            ModelVerificationResult(
                model_id="test/local-model",
                passed=True,
                phase_results=_make_phase_results(passed=True),
            ),
            ModelVerificationResult(
                model_id="test/openrouter-model",
                passed=False,
                phase_results=_make_phase_results(passed=False),
            ),
        ],
    )


def _make_mock_config() -> MagicMock:
    """Build a mock RunConfig with two endpoints.

    Returns:
        MagicMock: Config with endpoints attribute.
    """
    config = MagicMock()
    config.endpoints = EndpointSetConfig(
        default="openrouter",
        endpoints=[_LM_STUDIO_EP, _OPENROUTER_EP],
    )
    config.endpoint = None
    return config


def test_verify_models_help(runner: CliRunner) -> None:
    """Test verify-models --help displays usage information."""
    result = runner.invoke(app, ["verify-models", "--help"])

    assert result.exit_code == 0
    assert "--endpoint" in result.stdout
    assert "--model" in result.stdout


def test_verify_models_invalid_endpoint_filter(
    runner: CliRunner,
) -> None:
    """Test verify-models rejects invalid --endpoint values."""
    result = runner.invoke(app, ["verify-models", "--endpoint", "invalid"])

    assert result.exit_code == 11  # VALIDATION_ERROR
    assert "invalid" in result.stdout


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_all_pass(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test verify-models succeeds when all models pass."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_all_pass_result()

    result = runner.invoke(app, ["verify-models"])

    assert result.exit_code == 0
    mock_verify.assert_called_once()


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_failure_exits_nonzero(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test verify-models exits with code 1 when models fail."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_partial_fail_result()

    result = runner.invoke(app, ["verify-models"])

    assert result.exit_code == 1


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_endpoint_filter_passed_to_runner(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test --endpoint filter is forwarded to verify_registry."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_all_pass_result()

    result = runner.invoke(app, ["verify-models", "--endpoint", "local"])

    assert result.exit_code == 0
    call_kwargs = mock_verify.call_args[1]
    assert call_kwargs["endpoint_filter"] == "local"


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_model_filter_passed_to_runner(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test --model filter is forwarded to verify_registry."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_all_pass_result()

    result = runner.invoke(
        app,
        ["verify-models", "--model", "test/local-model"],
    )

    assert result.exit_code == 0
    call_kwargs = mock_verify.call_args[1]
    assert call_kwargs["model_filter"] == "test/local-model"


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_endpoint_all_treated_as_no_filter(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test --endpoint all passes None as filter."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_all_pass_result()

    result = runner.invoke(app, ["verify-models", "--endpoint", "all"])

    assert result.exit_code == 0
    call_kwargs = mock_verify.call_args[1]
    assert call_kwargs["endpoint_filter"] is None


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_builds_endpoints_map_from_config(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test endpoints are extracted from config and passed."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_all_pass_result()

    runner.invoke(app, ["verify-models"])

    call_kwargs = mock_verify.call_args[1]
    endpoints = call_kwargs["endpoints"]
    assert "lm-studio" in endpoints
    assert "openrouter" in endpoints
    assert endpoints["lm-studio"].base_url == "http://localhost:1234/v1"
    assert endpoints["openrouter"].base_url == "https://openrouter.ai/api/v1"


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_non_tty_json_output_all_pass(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test non-TTY output emits valid JSON when all models pass."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_all_pass_result()

    result = runner.invoke(app, ["verify-models"])

    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["passed"] is True
    assert len(parsed["model_results"]) == 2


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_non_tty_json_output_partial_fail(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test non-TTY output emits valid JSON when some models fail."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_partial_fail_result()

    result = runner.invoke(app, ["verify-models"])

    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["passed"] is False
    failed = [m for m in parsed["model_results"] if not m["passed"]]
    assert len(failed) == 1
    assert failed[0]["model_id"] == "test/openrouter-model"


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_tty_rich_table_output(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test TTY output renders a rich table with model results."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.return_value = _make_partial_fail_result()

    with patch("rentl.main.sys") as mock_sys:
        mock_sys.stdout.isatty.return_value = True
        result = runner.invoke(app, ["verify-models"])

    assert result.exit_code == 1
    # TTY output should contain table elements and model IDs
    assert "Model Verification Results" in result.stdout
    assert "test/local-model" in result.stdout
    assert "test/openrouter-model" in result.stdout
    # Should contain summary line
    assert "1/2 models passed" in result.stdout


@patch("rentl.main.verify_registry", new_callable=AsyncMock)
@patch("rentl.main.load_bundled_registry")
@patch("rentl.main._load_resolved_config")
def test_verify_models_runtime_error_returns_actionable_output(
    mock_config: MagicMock,
    mock_load_registry: MagicMock,
    mock_verify: AsyncMock,
    runner: CliRunner,
) -> None:
    """Test unexpected verifier exception returns actionable CLI output."""
    mock_config.return_value = _make_mock_config()
    mock_load_registry.return_value = _make_registry()
    mock_verify.side_effect = RuntimeError("connection refused by provider")

    result = runner.invoke(app, ["verify-models"])

    assert result.exit_code == 99  # RUNTIME_ERROR
    assert "Verification error" in result.stdout
    assert "connection refused by provider" in result.stdout
