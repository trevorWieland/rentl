"""BDD integration tests for status command cost display."""

from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid7

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import PhaseName, PhaseStatus
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    AgentUsageTotals,
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
    ProgressUpdate,
    RunProgress,
)

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.integration

scenarios("../features/cli/status_cost.feature")


def _write_config(config_dir: Path, workspace_dir: Path) -> Path:
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
        enabled = true

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
    file_path = config_dir / "rentl.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _make_summary() -> tuple[ProgressSummary, PhaseProgress, RunProgress]:
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.CONTEXT,
        status=PhaseStatus.COMPLETED,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_progress = RunProgress(
        phases=[phase_progress],
        summary=summary,
        phase_weights=None,
    )
    return summary, phase_progress, run_progress


class StatusCostContext:
    """Context object for status cost BDD scenarios."""

    config_path: Path | None = None
    workspace_dir: Path | None = None
    run_id: str = ""
    result: Result | None = None
    response: dict | None = None


@given("a workspace with progress data containing cost", target_fixture="ctx")
def given_workspace_with_cost(tmp_path: Path) -> StatusCostContext:
    """Set up workspace with agent progress data that includes cost information.

    Returns:
        StatusCostContext with cost-bearing progress data on disk.
    """
    ctx = StatusCostContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    ctx.config_path = _write_config(tmp_path, ctx.workspace_dir)
    run_id = uuid7()
    ctx.run_id = str(run_id)

    progress_dir = ctx.workspace_dir / "logs" / "progress"
    progress_dir.mkdir(parents=True)
    progress_path = progress_dir / f"{run_id}.jsonl"

    _, phase_progress, run_progress = _make_summary()

    completed_agent = AgentTelemetry(
        agent_run_id="agent_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.COMPLETED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:01:00Z",
        usage=AgentUsageTotals(
            input_tokens=500,
            output_tokens=200,
            total_tokens=700,
            request_count=1,
            tool_calls=0,
            cost_usd=0.0042,
        ),
        cost_usd=0.0042,
    )
    failed_agent = AgentTelemetry(
        agent_run_id="agent_002",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.FAILED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:00:30Z",
        usage=AgentUsageTotals(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            request_count=1,
            tool_calls=0,
            cost_usd=0.001,
        ),
        cost_usd=0.001,
    )

    lines = []
    for agent in [completed_agent, failed_agent]:
        update = ProgressUpdate(
            run_id=run_id,
            event=ProgressEvent.AGENT_COMPLETED
            if agent.status == AgentStatus.COMPLETED
            else ProgressEvent.AGENT_FAILED,
            timestamp="2026-02-03T12:01:00Z",
            phase=PhaseName.CONTEXT,
            phase_status=PhaseStatus.RUNNING,
            run_progress=run_progress,
            phase_progress=phase_progress,
            metric=None,
            agent_update=agent,
            message=None,
        )
        lines.append(update.model_dump_json())

    progress_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ctx


@given("a workspace with progress data without cost", target_fixture="ctx")
def given_workspace_without_cost(tmp_path: Path) -> StatusCostContext:
    """Set up workspace with agent progress data that has no cost information.

    Returns:
        StatusCostContext with cost-free progress data on disk.
    """
    ctx = StatusCostContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    ctx.config_path = _write_config(tmp_path, ctx.workspace_dir)
    run_id = uuid7()
    ctx.run_id = str(run_id)

    progress_dir = ctx.workspace_dir / "logs" / "progress"
    progress_dir.mkdir(parents=True)
    progress_path = progress_dir / f"{run_id}.jsonl"

    _, phase_progress, run_progress = _make_summary()

    agent = AgentTelemetry(
        agent_run_id="agent_001",
        agent_name="scene_summarizer",
        phase=PhaseName.CONTEXT,
        target_language=None,
        status=AgentStatus.COMPLETED,
        attempt=1,
        started_at="2026-02-03T12:00:00Z",
        completed_at="2026-02-03T12:01:00Z",
        usage=AgentUsageTotals(
            input_tokens=500,
            output_tokens=200,
            total_tokens=700,
            request_count=1,
            tool_calls=0,
        ),
    )

    update = ProgressUpdate(
        run_id=run_id,
        event=ProgressEvent.AGENT_COMPLETED,
        timestamp="2026-02-03T12:01:00Z",
        phase=PhaseName.CONTEXT,
        phase_status=PhaseStatus.RUNNING,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        agent_update=agent,
        message=None,
    )
    progress_path.write_text(update.model_dump_json() + "\n", encoding="utf-8")
    return ctx


@when("I run status with --json")
def when_run_status_json(ctx: StatusCostContext, cli_runner: CliRunner) -> None:
    """Invoke the status command with JSON output."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "status",
            "--config",
            str(ctx.config_path),
            "--run-id",
            ctx.run_id,
            "--json",
        ],
    )
    if ctx.result.stdout:
        parsed = json.loads(ctx.result.stdout)
        ctx.response = parsed.get("data", {})


@then("the command succeeds")
def then_command_succeeds(ctx: StatusCostContext) -> None:
    """Assert the CLI command exits with code 0."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}: {ctx.result.stdout}"
    )


@then("the JSON response includes total_cost_usd")
def then_includes_cost(ctx: StatusCostContext) -> None:
    """Assert the agent summary includes a positive total_cost_usd."""
    assert ctx.response is not None
    summary = ctx.response.get("agent_summary", {})
    assert summary.get("total_cost_usd") is not None
    assert summary["total_cost_usd"] > 0


@then("the JSON response includes waste_ratio")
def then_includes_waste_ratio(ctx: StatusCostContext) -> None:
    """Assert the agent summary includes a positive waste_ratio."""
    assert ctx.response is not None
    summary = ctx.response.get("agent_summary", {})
    assert "waste_ratio" in summary
    # With a failed agent, waste_ratio should be > 0
    assert summary["waste_ratio"] > 0


@then("the JSON response has null total_cost_usd")
def then_null_cost(ctx: StatusCostContext) -> None:
    """Assert the agent summary has null total_cost_usd."""
    assert ctx.response is not None
    summary = ctx.response.get("agent_summary", {})
    assert summary.get("total_cost_usd") is None


@then("the JSON response includes waste_ratio as 0.0")
def then_waste_ratio_zero(ctx: StatusCostContext) -> None:
    """Assert the agent summary has waste_ratio of zero."""
    assert ctx.response is not None
    summary = ctx.response.get("agent_summary", {})
    assert math.isclose(summary["waste_ratio"], 0.0, abs_tol=1e-9)
