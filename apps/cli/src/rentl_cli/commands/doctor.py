"""CLI command for onboarding and configuration smoke checks."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import ValidationError
from rentl_core.config.settings import get_settings
from rentl_core.context.project import load_project_context
from rentl_core.util.logging import configure_logging

from rentl_cli.cli_types import ProjectPathOption
from rentl_cli.commands.run import _collect_progress_snapshot


def doctor(
    project_path: ProjectPathOption = Path("."),
    verbosity: Annotated[
        Literal["info", "verbose", "debug"], typer.Option("--verbosity", "-v", help="Console verbosity level.")
    ] = "info",
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", help="Write detailed logs to this file (default: .rentl/logs/rentl.log)."),
    ] = None,
    skip_status: Annotated[bool, typer.Option(help="Skip reading project status snapshot.")] = False,
) -> None:
    """Run onboarding checks for configuration and project health.

    Raises:
        typer.Exit: When required configuration is missing or project load fails.
    """
    configure_logging(verbosity, log_file or project_path / ".rentl" / "logs" / "doctor.log")
    issues: list[str] = []

    typer.secho("rentl doctor", fg=typer.colors.CYAN, bold=True)

    # Required settings
    try:
        settings = get_settings()
    except ValidationError as exc:
        typer.secho("✗ LLM config: missing required environment variables", fg=typer.colors.RED)
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    missing_required: list[str] = []
    required_values = {
        "OPENAI_URL": settings.openai_url,
        "OPENAI_API_KEY": settings.openai_api_key.get_secret_value(),
        "LLM_MODEL": settings.llm_model,
    }
    for env_name, value in required_values.items():
        if not value:
            missing_required.append(env_name)
    if missing_required:
        typer.secho(f"✗ LLM config: missing {', '.join(missing_required)}", fg=typer.colors.RED)
        issues.extend(missing_required)
    else:
        typer.secho("✓ LLM config: OK", fg=typer.colors.GREEN)

    # Optional MTL
    if settings.mtl_url and settings.mtl_model and settings.mtl_api_key:
        typer.secho("✓ MTL config: OK (optional)", fg=typer.colors.GREEN)
    else:
        typer.secho("Info: MTL config not set (optional)", fg=typer.colors.YELLOW)

    import anyio

    async def _run_checks() -> None:
        # Project status
        try:
            context = await load_project_context(project_path)
        except FileNotFoundError as exc:
            typer.secho(f"✗ Project load failed: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc
        except ValidationError as exc:
            typer.secho(f"✗ Project load failed: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc
        except Exception as exc:
            typer.secho(f"✗ Project load failed with unexpected error: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc
        typer.secho(
            f"✓ Project loaded: {len(context.scenes)} scenes, {len(context.characters)} characters, "
            f"{len(context.locations)} locations, {len(context.routes)} routes",
            fg=typer.colors.GREEN,
        )

        if not skip_status:
            progress = await _collect_progress_snapshot(context)
            typer.secho(
                f"Status: translate {progress.translation_progress_pct:.1f}% "
                f"({progress.translated_lines}/{progress.total_lines} lines), "
                f"edit {progress.editing_progress_pct:.1f}% "
                f"({progress.checked_lines}/{progress.translated_lines or 1} translated lines), "
                f"failing checks {progress.failing_checks}",
                fg=typer.colors.CYAN,
            )

    anyio.run(_run_checks)

    if issues:
        raise typer.Exit(code=1)
    typer.secho("Doctor checks complete.", fg=typer.colors.GREEN, bold=True)
