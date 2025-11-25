"""CLI commands for running pipelines."""

from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from typing import Annotated, Literal
from uuid import uuid4

import typer
from rentl_core.util.logging import configure_logging
from rentl_pipelines.flows.context_builder import run_context_builder
from rentl_pipelines.flows.editor import run_editor
from rentl_pipelines.flows.translator import run_translator

from rentl_cli.cli_types import ProjectPathArgument
from rentl_cli.utils.baseline import write_baseline


def _prompt_decisions(requests: list[str]) -> list[str | dict[str, str]]:
    """Prompt the user for HITL decisions in the CLI.

    Args:
        requests: Approval request messages from the agent.

    Returns:
        list[str | dict[str, str]]: Decisions corresponding to each request.
    """
    decisions: list[str | dict[str, str]] = []
    for request in requests:
        typer.secho("\nHITL approval requested:", fg=typer.colors.YELLOW, bold=True)
        typer.echo(request)
        decision = typer.prompt("Decision [approve/reject]", default="approve")
        if decision.lower() not in {"approve", "reject"}:
            typer.secho("Invalid choice, defaulting to 'reject'.", fg=typer.colors.RED)
            decision = "reject"
        decisions.append(decision.lower())
    return decisions


def context(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    overwrite: Annotated[bool, typer.Option(help="Allow overwriting existing metadata.")] = False,
    mode: Annotated[
        Literal["overwrite", "gap-fill", "new-only"],
        typer.Option(help="Processing mode: overwrite, gap-fill (default), or new-only"),
    ] = "gap-fill",
    concurrency: Annotated[int, typer.Option(help="Maximum concurrent detailer runs.")] = 4,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Context Builder pipeline to enrich all game metadata."""
    configure_logging(verbose)
    typer.secho("Starting Context Builder pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = f"context-{uuid4()}"
    result = run_context_builder(
        project_path,
        allow_overwrite=overwrite,
        mode=mode,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
    )

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
    mode: Annotated[
        Literal["overwrite", "gap-fill", "new-only"],
        typer.Option(help="Processing mode: overwrite, gap-fill (default), or new-only"),
    ] = "gap-fill",
    concurrency: Annotated[int, typer.Option(help="Maximum concurrent scene translations.")] = 4,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Translator pipeline to translate scenes."""
    configure_logging(verbose)
    typer.secho("Starting Translator pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = f"translate-{uuid4()}"
    result = run_translator(
        project_path,
        scene_ids=scene_ids or None,
        allow_overwrite=overwrite,
        mode=mode,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
    )

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
    mode: Annotated[
        Literal["overwrite", "gap-fill", "new-only"],
        typer.Option(help="Processing mode: overwrite, gap-fill (default), or new-only"),
    ] = "gap-fill",
    concurrency: Annotated[int, typer.Option(help="Maximum concurrent QA runs.")] = 4,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Editor pipeline to perform QA on translations."""
    configure_logging(verbose)
    typer.secho("Starting Editor pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = f"edit-{uuid4()}"
    result = run_editor(
        project_path,
        scene_ids=scene_ids or None,
        mode=mode,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
    )

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
