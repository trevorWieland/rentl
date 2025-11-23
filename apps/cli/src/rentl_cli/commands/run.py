"""CLI commands for running pipelines."""

from __future__ import annotations

from pathlib import Path

import typer
from rentl_core.util.logging import configure_logging
from rentl_pipelines.flows.scene_mvp import run_scene_detail, run_scene_mvp

from rentl_cli.cli_types import ProjectPathArgument


def detail_scene(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    scene_id: str = typer.Argument(..., help="Scene identifier, e.g., scene_c_00."),
    overwrite: bool = typer.Option(False, help="Allow overwriting existing metadata."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging."),
) -> None:
    """Detail a single scene and display the resulting metadata."""
    configure_logging(verbose)
    result = run_scene_detail(project_path, scene_id, allow_overwrite=overwrite)
    if result:
        typer.secho(f"Metadata for {scene_id}:", fg=typer.colors.GREEN)
        typer.echo(f"  Summary: {result.summary}")
        typer.echo(f"  Tags: {', '.join(result.tags)}")
        typer.echo(f"  Characters: {', '.join(result.primary_characters)}")
        typer.echo(f"  Locations: {', '.join(result.locations)}")
    else:
        typer.secho(f"No metadata was created for {scene_id} (possibly skipped).", fg=typer.colors.YELLOW)


def detail_mvp(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    overwrite: bool = typer.Option(False, help="Allow overwriting existing metadata."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging."),
) -> None:
    """Detail every scene in the project."""
    configure_logging(verbose)
    results = run_scene_mvp(project_path, allow_overwrite=overwrite)
    if not results:
        typer.secho("No scenes were detailed (already up-to-date?).", fg=typer.colors.YELLOW)
        return

    for scene_id, result in results.items():
        typer.echo(f"[{scene_id}] {result.summary}")
