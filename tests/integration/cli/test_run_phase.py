"""BDD integration tests for run-phase CLI command."""

from __future__ import annotations

import json
import shutil
import textwrap
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_agents.runtime import ProfileAgent
from rentl_schemas.config import RunConfig

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.integration

# Link feature file
scenarios("../features/cli/run_phase.feature")


def _write_phase_config(config_path: Path, workspace_dir: Path) -> Path:
    """Write a rentl.toml config for phase tests.

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
        target_languages = ["en", "de"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [agents]
        prompts_dir = "{workspace_dir}/prompts"
        agents_dir = "{workspace_dir}/agents"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "http://localhost:8001/v1"
        api_key_env = "PRIMARY_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "primary"

        [[pipeline.phases]]
        phase = "ingest"

        [[pipeline.phases]]
        phase = "context"
        agents = ["context_agent"]

        [[pipeline.phases]]
        phase = "pretranslation"
        agents = ["pretranslation_agent"]

        [[pipeline.phases]]
        phase = "translate"
        agents = ["translate_agent"]

        [[pipeline.phases]]
        phase = "qa"
        agents = ["qa_agent"]

        [[pipeline.phases]]
        phase = "edit"
        agents = ["edit_agent"]

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

    # Round-trip schema validation: ensure written config is a valid RunConfig
    with file_path.open("rb") as f:
        RunConfig.model_validate(tomllib.load(f))

    return file_path


class PhaseContext:
    """Context object for run-phase BDD scenarios."""

    config_path: Path | None = None
    workspace_dir: Path | None = None
    result: Result | None = None
    response: dict | None = None


@given("a rentl config with all phases configured", target_fixture="ctx")
def given_config_all_phases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> PhaseContext:
    """Create a config with all phases.

    Returns:
        PhaseContext with workspace and config initialized.
    """
    ctx = PhaseContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    ctx.config_path = _write_phase_config(tmp_path, ctx.workspace_dir)
    monkeypatch.setenv("PRIMARY_KEY", "fake-key")

    # Mock at agent boundary (ProfileAgent.run)
    mock_call_count = {"count": 0}

    async def mock_agent_run(  # noqa: RUF029
        self: ProfileAgent, payload: object
    ) -> object:  # pragma: no cover - ingest-only test doesn't invoke agents
        mock_call_count["count"] += 1
        raise RuntimeError("Unexpected agent invocation in ingest-only phase test")

    monkeypatch.setattr(ProfileAgent, "run", mock_agent_run)
    ctx.mock_call_count = mock_call_count  # type: ignore[attr-defined]
    return ctx


@given("an input file with source lines for phase test")
def given_input_file_for_phase(ctx: PhaseContext) -> None:
    """Create an input file with source lines."""
    assert ctx.workspace_dir is not None
    input_path = ctx.workspace_dir / "input.txt"
    input_path.write_text("こんにちは\nさようなら\n", encoding="utf-8")


@given("no prior run state exists")
def given_no_prior_run_state(ctx: PhaseContext) -> None:
    """Ensure no prior run state exists."""
    assert ctx.workspace_dir is not None
    run_state_dir = ctx.workspace_dir / ".rentl" / "run_state"
    if run_state_dir.exists():
        shutil.rmtree(run_state_dir)


@when("I run the ingest phase")
def when_run_ingest_phase(ctx: PhaseContext, cli_runner: CliRunner) -> None:
    """Run the run-phase CLI command for ingest."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["run-phase", "--config", str(ctx.config_path), "--phase", "ingest"],
    )
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@when("I run the export phase without target language")
def when_run_export_phase_no_target(ctx: PhaseContext, cli_runner: CliRunner) -> None:
    """Run the run-phase CLI command for export without target language."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "run-phase",
            "--config",
            str(ctx.config_path),
            "--phase",
            "export",
        ],
    )
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@then("the response contains phase run data")
def then_response_contains_phase_data(ctx: PhaseContext) -> None:
    """Assert the response contains phase run data."""
    assert ctx.response is not None
    assert ctx.response.get("error") is None, (
        f"Unexpected error: {ctx.response.get('error')}"
    )
    assert ctx.response.get("data") is not None
    assert ctx.response["data"].get("run_id") is not None

    # Verify agent mock was NOT called (ingest-only phase doesn't invoke agents)
    assert ctx.mock_call_count["count"] == 0, (  # type: ignore[attr-defined]
        f"ProfileAgent.run was called {ctx.mock_call_count['count']} times "  # type: ignore[attr-defined]
        "in an ingest-only phase test — agents should not be invoked"
    )
