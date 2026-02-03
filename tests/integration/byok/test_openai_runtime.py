"""BDD integration tests for OpenAI-compatible BYOK runtime."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_bdd import given, scenarios, then, when

from rentl_core.llm.connection import LlmConnectionTarget, build_connection_plan
from rentl_schemas.config import RunConfig
from rentl_schemas.llm import LlmEndpointTarget
from rentl_schemas.validation import validate_run_config

if TYPE_CHECKING:
    import pytest

# Link feature file
scenarios("../features/byok/openai_runtime.feature")


def _write_byok_config(config_path: Path, workspace_dir: Path) -> Path:
    """Write a rentl.toml config for BYOK tests.

    Returns:
        Path to the written config file.
    """
    content = textwrap.dedent(
        f"""\
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "test-project"

        [project.paths]
        workspace_dir = "{workspace_dir}"
        input_path = "input.txt"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "txt"
        output_format = "txt"

        [project.languages]
        source_language = "ja"
        target_languages = ["en"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "http://localhost:8001/v1"
        api_key_env = "PRIMARY_KEY"

        [[endpoints.endpoints]]
        provider_name = "secondary"
        base_url = "http://localhost:8002/v1"
        api_key_env = "SECONDARY_KEY"

        [[endpoints.endpoints]]
        provider_name = "unused"
        base_url = "http://localhost:8003/v1"
        api_key_env = "UNUSED_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "primary"

        [[pipeline.phases]]
        phase = "ingest"

        [[pipeline.phases]]
        phase = "context"

        [[pipeline.phases]]
        phase = "pretranslation"

        [[pipeline.phases]]
        phase = "translate"

        [pipeline.phases.model]
        model_id = "gpt-4"
        endpoint_ref = "secondary"

        [[pipeline.phases]]
        phase = "qa"

        [[pipeline.phases]]
        phase = "edit"

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
    )
    file_path = config_path / "rentl.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _load_run_config(config_path: Path) -> RunConfig:
    """Load a run config from a TOML file.

    Returns:
        Parsed and validated RunConfig.
    """
    import tomllib

    with open(config_path, "rb") as handle:
        payload = tomllib.load(handle)
    return validate_run_config(payload)


class ByokContext:
    """Context object for BYOK BDD scenarios."""

    config_path: Path | None = None
    workspace_dir: Path | None = None
    config: RunConfig | None = None
    targets: list[LlmConnectionTarget] | None = None
    skipped: list[LlmEndpointTarget] | None = None


@given("a config with multiple BYOK endpoints", target_fixture="ctx")
def given_config_with_endpoints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> ByokContext:
    """Create a config with multiple BYOK endpoints.

    Returns:
        ByokContext with workspace and config initialized.
    """
    ctx = ByokContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    (ctx.workspace_dir / "input.txt").write_text("Hello\n", encoding="utf-8")
    ctx.config_path = _write_byok_config(tmp_path, ctx.workspace_dir)
    ctx.config = _load_run_config(ctx.config_path)

    # Set API keys for used endpoints
    monkeypatch.setenv("PRIMARY_KEY", "fake-primary-key")
    monkeypatch.setenv("SECONDARY_KEY", "fake-secondary-key")
    # UNUSED_KEY is intentionally not set

    return ctx


@given("a config with endpoints requiring API keys", target_fixture="ctx")
def given_config_requiring_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> ByokContext:
    """Create a config with endpoints requiring API keys.

    Returns:
        ByokContext with workspace, config, and partial API keys.
    """
    ctx = ByokContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    (ctx.workspace_dir / "input.txt").write_text("Hello\n", encoding="utf-8")
    ctx.config_path = _write_byok_config(tmp_path, ctx.workspace_dir)
    ctx.config = _load_run_config(ctx.config_path)

    # Only set primary key, secondary is missing
    monkeypatch.setenv("PRIMARY_KEY", "fake-primary-key")
    # Clear SECONDARY_KEY if it exists
    monkeypatch.delenv("SECONDARY_KEY", raising=False)

    return ctx


@given("some API keys are missing from environment")
def given_some_keys_missing() -> None:
    """Confirm some API keys are missing (already handled in fixture)."""


@when("I build the connection plan")
def when_build_connection_plan(ctx: ByokContext) -> None:
    """Build the connection validation plan."""
    assert ctx.config is not None
    targets, skipped = build_connection_plan(ctx.config)
    ctx.targets = targets
    ctx.skipped = skipped


@then("the plan contains validation targets for used endpoints")
def then_plan_has_targets(ctx: ByokContext) -> None:
    """Assert the plan contains validation targets."""
    assert ctx.targets is not None
    # Should have targets for primary and secondary (used endpoints)
    provider_names = {t.runtime.endpoint.provider_name for t in ctx.targets}
    assert "primary" in provider_names
    assert "secondary" in provider_names


@then("unused endpoints are marked as skipped")
def then_unused_skipped(ctx: ByokContext) -> None:
    """Assert unused endpoints are skipped."""
    assert ctx.skipped is not None
    skipped_names = {e.provider_name for e in ctx.skipped}
    assert "unused" in skipped_names


@then("endpoints with missing keys are included")
def then_missing_keys_included(ctx: ByokContext) -> None:
    """Assert endpoints with missing keys are still in targets."""
    assert ctx.targets is not None
    # Secondary is used but key is missing - it should still be in targets
    # (validation will fail when we try to use it, but it's planned)
    provider_names = {t.runtime.endpoint.provider_name for t in ctx.targets}
    assert "secondary" in provider_names
