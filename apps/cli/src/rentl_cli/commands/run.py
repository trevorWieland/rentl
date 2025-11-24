"""CLI commands for running pipelines."""

from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from typing import Annotated

import typer
from rentl_core.util.logging import configure_logging
from rentl_pipelines.flows.context_builder import run_context_builder
from rentl_pipelines.flows.editor import run_editor
from rentl_pipelines.flows.scene_mvp import run_scene_detail, run_scene_mvp
from rentl_pipelines.flows.translator import run_translator

from rentl_cli.cli_types import ProjectPathArgument
from rentl_cli.utils.baseline import write_baseline


def detail_scene(
    scene_id: Annotated[str, typer.Argument(help="Scene identifier, e.g., scene_c_00.")],
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    overwrite: Annotated[bool, typer.Option(help="Allow overwriting existing metadata.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
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
    overwrite: Annotated[bool, typer.Option(help="Allow overwriting existing metadata.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Detail every scene in the project."""
    configure_logging(verbose)
    results = run_scene_mvp(project_path, allow_overwrite=overwrite)
    if not results:
        typer.secho("No scenes were detailed (already up-to-date?).", fg=typer.colors.YELLOW)
        return

    for scene_id, result in results.items():
        typer.echo(f"[{scene_id}] {result.summary}")


def context(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    overwrite: Annotated[bool, typer.Option(help="Allow overwriting existing metadata.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Context Builder pipeline to enrich all game metadata."""
    configure_logging(verbose)
    typer.secho("Starting Context Builder pipeline...", fg=typer.colors.CYAN, bold=True)

    result = run_context_builder(project_path, allow_overwrite=overwrite)

    # Display results
    typer.secho("\nContext Builder Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes detailed: {result.scenes_detailed}")
    typer.echo(f"  Characters detailed: {result.characters_detailed}")
    typer.echo(f"  Locations detailed: {result.locations_detailed}")
    typer.echo(f"  Glossary entries added: {result.glossary_entries_added}")
    typer.echo(f"  Glossary entries updated: {result.glossary_entries_updated}")
    typer.echo(f"  Routes detailed: {result.routes_detailed}")


def translate(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    scene_ids: Annotated[
        list[str] | None, typer.Option("--scene", "-s", help="Specific scene IDs to translate (default: all).")
    ] = None,
    overwrite: Annotated[bool, typer.Option(help="Allow overwriting existing translations.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Translator pipeline to translate scenes."""
    configure_logging(verbose)
    typer.secho("Starting Translator pipeline...", fg=typer.colors.CYAN, bold=True)

    result = run_translator(project_path, scene_ids=scene_ids or None, allow_overwrite=overwrite)

    # Display results
    typer.secho("\nTranslator Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes translated: {result.scenes_translated}")
    typer.echo(f"  Lines translated: {result.lines_translated}")
    typer.echo(f"  Scenes skipped: {result.scenes_skipped}")


def edit(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    scene_ids: Annotated[
        list[str] | None, typer.Option("--scene", "-s", help="Specific scene IDs to QA (default: all).")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Editor pipeline to perform QA on translations."""
    configure_logging(verbose)
    typer.secho("Starting Editor pipeline...", fg=typer.colors.CYAN, bold=True)

    result = run_editor(project_path, scene_ids=scene_ids or None)

    typer.secho("\nEditor Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes checked: {result.scenes_checked}")


def reset_example(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
) -> None:
    """Reset example project metadata/output to a clean baseline for repeatable tests."""
    output_dir = project_path / "output"
    if output_dir.exists():
        rmtree(output_dir)

    metadata_dir = project_path / "metadata"
    if metadata_dir.exists():
        rmtree(metadata_dir)

    # Regenerate from Pydantic models
    typer.echo(f"Regenerating baseline into {project_path}")
    import anyio

    anyio.run(write_baseline, project_path)
    typer.secho(f"Reset {project_path} to baseline data.", fg=typer.colors.GREEN)
