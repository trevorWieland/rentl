"""CLI commands for running pipelines."""

from __future__ import annotations

from pathlib import Path

import typer
from rentl_pipelines.flows.scene_mvp import run_scene_mvp, run_scene_summary

from rentl_cli.cli_types import ProjectPathArgument


def summarize_scene(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    scene_id: str = typer.Argument(..., help="Scene identifier, e.g., scene_c_00."),
    overwrite: bool = typer.Option(False, help="Allow overwriting existing summaries."),
) -> None:
    """Summarize a single scene and display the resulting summary."""
    summary = run_scene_summary(project_path, scene_id, allow_overwrite=overwrite)
    if summary:
        typer.secho(f"Summary for {scene_id}:\n{summary}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"No summary was created for {scene_id} (possibly skipped).", fg=typer.colors.YELLOW)


def summarize_mvp(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    overwrite: bool = typer.Option(False, help="Allow overwriting existing summaries."),
) -> None:
    """Summarize every scene in the project."""
    results = run_scene_mvp(project_path, allow_overwrite=overwrite)
    if not results:
        typer.secho("No scenes were summarized (already up-to-date?).", fg=typer.colors.YELLOW)
        return

    for scene_id, summary in results.items():
        typer.echo(f"[{scene_id}] {summary}")
