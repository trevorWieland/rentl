"""CLI command for validating rentl project data."""

from __future__ import annotations

from pathlib import Path

import anyio
import typer
from rentl_core.io.loader import (
    load_character_metadata,
    load_game_metadata,
    load_glossary_entries,
    load_location_metadata,
    load_route_metadata,
    load_scene_file,
    load_scene_metadata,
)
from rentl_core.util.logging import configure_logging

from rentl_cli.cli_types import ProjectPathArgument


async def _validate_async(project_path: Path) -> None:
    """Validate metadata and scene files located under *project_path*."""
    metadata_dir = project_path / "metadata"
    input_dir = project_path / "input" / "scenes"

    await load_game_metadata(metadata_dir / "game.json")
    await load_character_metadata(metadata_dir / "characters.jsonl")
    await load_glossary_entries(metadata_dir / "glossary.jsonl")
    await load_location_metadata(metadata_dir / "locations.jsonl")

    routes = await load_route_metadata(metadata_dir / "routes.jsonl")
    scenes = await load_scene_metadata(metadata_dir / "scenes.jsonl")

    scene_ids = {scene.id for scene in scenes}
    route_ids = {route.id for route in routes}

    def _raise_unknown_scenes(route_id: str, missing: list[str]) -> None:
        joined = ", ".join(missing)
        message = f"Route '{route_id}' references unknown scenes: {joined}"
        raise ValueError(message)

    def _raise_unknown_routes(scene_id: str, missing: list[str]) -> None:
        joined = ", ".join(missing)
        message = f"Scene '{scene_id}' references unknown routes: {joined}"
        raise ValueError(message)

    def _raise_missing_scene_file(scene_path: Path) -> None:
        message = f"Missing scene file: {scene_path}"
        raise FileNotFoundError(message)

    for route in routes:
        missing = [scene_id for scene_id in route.scene_ids if scene_id not in scene_ids]
        if missing:
            _raise_unknown_scenes(route.id, missing)

    for scene in scenes:
        missing = [route_id for route_id in scene.route_ids if route_id not in route_ids]
        if missing:
            _raise_unknown_routes(scene.id, missing)

    for scene in scenes:
        scene_path = input_dir / f"{scene.id}.jsonl"
        if not scene_path.exists():
            _raise_missing_scene_file(scene_path)
        await load_scene_file(scene_path)


def validate(
    project_path: ProjectPathArgument = Path("examples/tiny_vn"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging."),
) -> None:
    """Run validation and exit with status 0 on success.

    Raises:
        typer.Exit: If validation encounters errors.
    """
    configure_logging(verbose)
    try:
        anyio.run(_validate_async, project_path)
    except Exception as exc:
        typer.secho(f"Validation failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.secho("Validation successful.", fg=typer.colors.GREEN)
