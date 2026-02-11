"""Diagnostic checks for rentl configuration and environment.

Provides health checks for Python version, config files, workspace structure,
API keys, and LLM connectivity. All checks return CheckResult with actionable
fix suggestions.
"""

from __future__ import annotations

import os
import sys
import tomllib
from enum import StrEnum
from pathlib import Path
from typing import cast

from pydantic import Field

from rentl_core.llm.connection import build_connection_plan, validate_connections
from rentl_core.migrate import ConfigDict, auto_migrate_config, dict_to_toml
from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import RunConfig
from rentl_schemas.exit_codes import ExitCode
from rentl_schemas.llm import (
    LlmConnectionReport,
    LlmConnectionStatus,
    LlmEndpointTarget,
)
from rentl_schemas.primitives import JsonValue
from rentl_schemas.validation import validate_run_config
from rentl_schemas.version import CURRENT_SCHEMA_VERSION, VersionInfo


def _load_config_sync(config_path: Path) -> RunConfig | None:
    """Load and validate config from path (synchronous helper).

    Auto-migrates the config if schema version is outdated before validation.

    Args:
        config_path: Path to rentl.toml config file.

    Returns:
        RunConfig if successful, None otherwise.
    """
    try:
        with open(config_path, "rb") as handle:
            payload = tomllib.load(handle)

        # Auto-migrate if needed
        target_version = VersionInfo(
            major=CURRENT_SCHEMA_VERSION[0],
            minor=CURRENT_SCHEMA_VERSION[1],
            patch=CURRENT_SCHEMA_VERSION[2],
        )
        config_dict = cast(ConfigDict, payload)
        migrated_config, was_migrated = auto_migrate_config(config_dict, target_version)

        # If migration occurred, back up and write the migrated config
        if was_migrated:
            backup_path = config_path.with_suffix(".toml.bak")
            backup_path.write_bytes(config_path.read_bytes())

            # Write migrated config
            migrated_toml = dict_to_toml(migrated_config)
            config_path.write_text(migrated_toml, encoding="utf-8")

        # Cast to JsonValue dict for validation (ConfigValue is compatible)
        payload_for_validation = cast(dict[str, JsonValue], migrated_config)
        return validate_run_config(payload_for_validation)
    except Exception:
        return None


class CheckStatus(StrEnum):
    """Status result for a diagnostic check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class CheckResult(BaseSchema):
    """Result from a single diagnostic check."""

    name: str = Field(..., min_length=1, description="Name of the check")
    status: CheckStatus = Field(..., description="Pass/warn/fail status")
    message: str = Field(..., min_length=1, description="Human-readable result message")
    fix_suggestion: str | None = Field(
        None, description="Actionable fix suggestion for failures/warnings"
    )


class DoctorReport(BaseSchema):
    """Aggregated diagnostic report from all checks."""

    checks: list[CheckResult] = Field(..., description="Individual check results")
    overall_status: CheckStatus = Field(
        ..., description="Worst status across all checks"
    )
    exit_code: ExitCode = Field(
        ..., description="Suggested exit code based on failures"
    )


def check_python_version() -> CheckResult:
    """Check if Python version meets minimum requirements.

    Returns:
        CheckResult: Check result with version info.
    """
    major, minor = sys.version_info.major, sys.version_info.minor
    version_str = f"{major}.{minor}.{sys.version_info.micro}"

    # Minimum required: Python 3.11
    if major < 3 or (major == 3 and minor < 11):
        return CheckResult(
            name="Python Version",
            status=CheckStatus.FAIL,
            message=f"Python {version_str} detected (minimum required: 3.11)",
            fix_suggestion=(
                "Install Python 3.11 or later and recreate your virtual environment"
            ),
        )

    return CheckResult(
        name="Python Version",
        status=CheckStatus.PASS,
        message=f"Python {version_str} meets requirements (>= 3.11)",
        fix_suggestion=None,
    )


def check_config_file(config_path: Path) -> CheckResult:
    """Check if config file exists at the given path.

    Args:
        config_path: Path to rentl.toml config file.

    Returns:
        CheckResult: Check result for config file presence.
    """
    if not config_path.exists():
        return CheckResult(
            name="Config File",
            status=CheckStatus.FAIL,
            message=f"Config file not found: {config_path}",
            fix_suggestion=(
                f"Run 'rentl init' to create {config_path.name} or specify a "
                f"different path with --config"
            ),
        )

    if not config_path.is_file():
        return CheckResult(
            name="Config File",
            status=CheckStatus.FAIL,
            message=f"Config path exists but is not a file: {config_path}",
            fix_suggestion=(
                f"Remove or rename the directory at {config_path} and run 'rentl init'"
            ),
        )

    return CheckResult(
        name="Config File",
        status=CheckStatus.PASS,
        message=f"Config file exists: {config_path}",
        fix_suggestion=None,
    )


def check_config_valid(config_path: Path) -> CheckResult:
    """Check if config file is valid TOML and passes schema validation.

    Auto-migrates the config if schema version is outdated before validation.

    Args:
        config_path: Path to rentl.toml config file.

    Returns:
        CheckResult: Check result for config validity.
    """
    if not config_path.exists():
        # Dependency: config file must exist first
        return CheckResult(
            name="Config Valid",
            status=CheckStatus.FAIL,
            message="Cannot validate config (file does not exist)",
            fix_suggestion="Resolve 'Config File' check first",
        )

    try:
        with open(config_path, "rb") as handle:
            payload = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        error_msg = str(exc).split("\n")[0]  # First line of error
        return CheckResult(
            name="Config Valid",
            status=CheckStatus.FAIL,
            message=f"Config TOML syntax error: {error_msg}",
            fix_suggestion=f"Fix TOML syntax errors in {config_path}",
        )
    except OSError as exc:
        return CheckResult(
            name="Config Valid",
            status=CheckStatus.FAIL,
            message=f"Cannot read config file: {exc}",
            fix_suggestion=f"Check file permissions for {config_path}",
        )

    try:
        # Auto-migrate if needed
        target_version = VersionInfo(
            major=CURRENT_SCHEMA_VERSION[0],
            minor=CURRENT_SCHEMA_VERSION[1],
            patch=CURRENT_SCHEMA_VERSION[2],
        )
        config_dict = cast(ConfigDict, payload)
        migrated_config, was_migrated = auto_migrate_config(config_dict, target_version)

        # If migration occurred, back up and write the migrated config
        if was_migrated:
            backup_path = config_path.with_suffix(".toml.bak")
            backup_path.write_bytes(config_path.read_bytes())

            # Write migrated config
            migrated_toml = dict_to_toml(migrated_config)
            config_path.write_text(migrated_toml, encoding="utf-8")

        # Cast to JsonValue dict for validation (ConfigValue is compatible)
        payload_for_validation = cast(dict[str, JsonValue], migrated_config)
        validate_run_config(payload_for_validation)
    except Exception as exc:
        error_msg = str(exc).split("\n")[0]  # First line of error
        return CheckResult(
            name="Config Valid",
            status=CheckStatus.FAIL,
            message=f"Config validation error: {error_msg}",
            fix_suggestion=(
                f"Fix validation errors in {config_path} (check "
                f"schema_version, required fields, phase configuration)"
            ),
        )

    return CheckResult(
        name="Config Valid",
        status=CheckStatus.PASS,
        message="Config file is valid",
        fix_suggestion=None,
    )


def check_workspace_dirs(config: RunConfig) -> CheckResult:
    """Check if required workspace directories exist.

    Args:
        config: Validated run configuration.

    Returns:
        CheckResult: Check result for workspace directory structure.
    """
    workspace_dir = Path(config.project.paths.workspace_dir)
    output_dir = Path(config.project.paths.output_dir)
    logs_dir = Path(config.project.paths.logs_dir)

    missing: list[str] = []
    if not workspace_dir.exists():
        missing.append(f"workspace ({workspace_dir})")
    if not output_dir.exists():
        missing.append(f"output ({output_dir})")
    if not logs_dir.exists():
        missing.append(f"logs ({logs_dir})")

    if missing:
        # Build mkdir command with all missing directories
        missing_paths = []
        if not workspace_dir.exists():
            missing_paths.append(str(workspace_dir))
        if not output_dir.exists():
            missing_paths.append(str(output_dir))
        if not logs_dir.exists():
            missing_paths.append(str(logs_dir))

        dirs_cmd = " ".join(missing_paths)
        return CheckResult(
            name="Workspace Directories",
            status=CheckStatus.FAIL,
            message=f"Missing directories: {', '.join(missing)}",
            fix_suggestion=f"Create missing directories: mkdir -p {dirs_cmd}",
        )

    return CheckResult(
        name="Workspace Directories",
        status=CheckStatus.PASS,
        message="All workspace directories exist",
        fix_suggestion=None,
    )


def check_api_keys(config: RunConfig) -> CheckResult:
    """Check if required API keys are present in environment.

    Args:
        config: Validated run configuration.

    Returns:
        CheckResult: Check result for API key availability.
    """
    required_keys: set[str] = set()

    # Check legacy endpoint config
    if config.endpoint is not None:
        required_keys.add(config.endpoint.api_key_env)

    # Check multi-endpoint config
    if config.endpoints is not None:
        required_keys.update(ep.api_key_env for ep in config.endpoints.endpoints)

    missing: list[str] = []
    for key_name in sorted(required_keys):
        if not os.environ.get(key_name):
            missing.append(key_name)

    if missing:
        # Note: doctor now loads .env and .env.local from config directory
        keys_list = " ".join(f"{k}=your_key_here" for k in missing)
        return CheckResult(
            name="API Keys",
            status=CheckStatus.FAIL,
            message=f"Missing API keys: {', '.join(missing)}",
            fix_suggestion=(
                f"Create .env file in config directory with: echo '{keys_list}' >> .env"
            ),
        )

    return CheckResult(
        name="API Keys",
        status=CheckStatus.PASS,
        message=f"All {len(required_keys)} API key(s) present in environment",
        fix_suggestion=None,
    )


async def check_llm_connectivity(
    runtime: LlmRuntimeProtocol, config: RunConfig
) -> CheckResult:
    """Check LLM endpoint connectivity with a test prompt.

    Args:
        runtime: LLM runtime adapter for making API calls.
        config: Validated run configuration.

    Returns:
        CheckResult: Check result for LLM connectivity.
    """
    targets, skipped = build_connection_plan(config)

    if not targets:
        return CheckResult(
            name="LLM Connectivity",
            status=CheckStatus.WARN,
            message="No LLM phases configured for connectivity check",
            fix_suggestion=(
                "Configure at least one LLM phase (context, pretranslation, "
                "translate, qa, edit) in rentl.toml"
            ),
        )

    def api_key_lookup(endpoint: LlmEndpointTarget) -> str | None:
        return os.environ.get(endpoint.api_key_env)

    report: LlmConnectionReport = await validate_connections(
        runtime=runtime,
        targets=targets,
        prompt="Test connectivity.",
        system_prompt="Respond with OK.",
        api_key_lookup=api_key_lookup,
        skipped_endpoints=skipped,
    )

    if report.failure_count > 0:
        failed_endpoints = [
            r.provider_name
            for r in report.results
            if r.status == LlmConnectionStatus.FAILED
        ]
        count_str = f"{report.failure_count}/{len(report.results)}"
        endpoint_list = ", ".join(failed_endpoints)
        return CheckResult(
            name="LLM Connectivity",
            status=CheckStatus.FAIL,
            message=f"{count_str} endpoint(s) failed: {endpoint_list}",
            fix_suggestion=(
                "Verify API keys in .env file (doctor loads .env and .env.local), "
                "check network connectivity, and confirm endpoint URLs are reachable. "
                "Use 'rentl validate-connection' for details."
            ),
        )

    if report.skipped_count > 0 and report.success_count == 0:
        return CheckResult(
            name="LLM Connectivity",
            status=CheckStatus.WARN,
            message=(
                f"{report.skipped_count} endpoint(s) skipped (no model configured)"
            ),
            fix_suggestion=(
                "Configure model_id for phases in rentl.toml to enable "
                "connectivity checks"
            ),
        )

    return CheckResult(
        name="LLM Connectivity",
        status=CheckStatus.PASS,
        message=f"All {report.success_count} endpoint(s) reachable",
        fix_suggestion=None,
    )


async def run_doctor(
    config_path: Path, *, runtime: LlmRuntimeProtocol | None = None
) -> DoctorReport:
    """Run all diagnostic checks and return aggregated report.

    Args:
        config_path: Path to rentl.toml config file.
        runtime: Optional LLM runtime for connectivity checks. If None, connectivity
            check will be skipped.

    Returns:
        DoctorReport: Aggregated results from all checks.
    """
    checks: list[CheckResult] = []

    # Check 1: Python version
    checks.append(check_python_version())

    # Check 2: Config file exists
    config_file_check = check_config_file(config_path)
    checks.append(config_file_check)

    # Check 3: Config file is valid (depends on Check 2)
    config_valid_check = check_config_valid(config_path)
    checks.append(config_valid_check)

    # Load config for remaining checks (if valid)
    config: RunConfig | None = None
    if config_valid_check.status == CheckStatus.PASS:
        config = _load_config_sync(config_path)

    # Check 4: Workspace directories (depends on valid config)
    if config is not None:
        checks.append(check_workspace_dirs(config))
    else:
        checks.append(
            CheckResult(
                name="Workspace Directories",
                status=CheckStatus.FAIL,
                message="Cannot check workspace directories (config invalid)",
                fix_suggestion="Resolve 'Config Valid' check first",
            )
        )

    # Check 5: API keys (depends on valid config)
    if config is not None:
        checks.append(check_api_keys(config))
    else:
        checks.append(
            CheckResult(
                name="API Keys",
                status=CheckStatus.FAIL,
                message="Cannot check API keys (config invalid)",
                fix_suggestion="Resolve 'Config Valid' check first",
            )
        )

    # Check 6: LLM connectivity (depends on valid config and runtime)
    if config is not None and runtime is not None:
        checks.append(await check_llm_connectivity(runtime, config))
    elif config is None:
        checks.append(
            CheckResult(
                name="LLM Connectivity",
                status=CheckStatus.FAIL,
                message="Cannot check LLM connectivity (config invalid)",
                fix_suggestion="Resolve 'Config Valid' check first",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="LLM Connectivity",
                status=CheckStatus.WARN,
                message="LLM connectivity check skipped (no runtime provided)",
                fix_suggestion=(
                    "LLM connectivity check requires runtime initialization. "
                    "This is typically handled automatically by CLI commands."
                ),
            )
        )

    # Determine overall status
    has_fail = any(check.status == CheckStatus.FAIL for check in checks)
    has_warn = any(check.status == CheckStatus.WARN for check in checks)

    if has_fail:
        overall_status = CheckStatus.FAIL
        # Determine appropriate exit code based on which checks failed
        # Precedence: config checks fail → CONFIG_ERROR
        # (even if connectivity also fails)
        # Only use CONNECTION_ERROR if connectivity fails but all config checks pass
        config_checks_failed = any(
            check.status == CheckStatus.FAIL
            and check.name
            in ("Config File", "Config Valid", "Workspace Directories", "API Keys")
            for check in checks
        )
        llm_check = next((c for c in checks if c.name == "LLM Connectivity"), None)

        if config_checks_failed:
            exit_code = ExitCode.CONFIG_ERROR
        elif (
            llm_check
            and llm_check.status == CheckStatus.FAIL
            and "config invalid" not in llm_check.message.lower()
        ):
            exit_code = ExitCode.CONNECTION_ERROR
        else:
            exit_code = ExitCode.CONFIG_ERROR
    elif has_warn:
        overall_status = CheckStatus.WARN
        exit_code = ExitCode.SUCCESS
    else:
        overall_status = CheckStatus.PASS
        exit_code = ExitCode.SUCCESS

    return DoctorReport(
        checks=checks, overall_status=overall_status, exit_code=exit_code
    )
