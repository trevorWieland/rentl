"""Scene-level pipelines for detailing MVP."""

from __future__ import annotations

from functools import partial
from pathlib import Path

import anyio
from rentl_agents.subagents.scene_detailer import SceneDetailResult, detail_scene
from rentl_core.context.project import load_project_context
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


async def _run_scene_mvp_async(
    project_path: Path,
    *,
    scene_id: str | None = None,
    allow_overwrite: bool = False,
) -> dict[str, SceneDetailResult]:
    """Detail all target scenes and return their metadata.

    Returns:
        dict[str, SceneDetailResult]: Mapping of scene ids to generated metadata.
    """
    context = await load_project_context(project_path)
    target_ids = [scene_id] if scene_id else sorted(context.scenes.keys())
    results: dict[str, SceneDetailResult] = {}

    for sid in target_ids:
        logger.info("Detailing scene %s", sid)
        metadata = await detail_scene(context, sid, allow_overwrite=allow_overwrite)
        results[sid] = metadata

    return results


def run_scene_mvp(project_path: Path, *, allow_overwrite: bool = False) -> dict[str, SceneDetailResult]:
    """Detail every scene in *project_path* and return metadata.

    Returns:
        dict[str, SceneDetailResult]: Mapping of scene ids to generated metadata.
    """
    return anyio.run(partial(_run_scene_mvp_async, project_path, allow_overwrite=allow_overwrite))


def run_scene_detail(project_path: Path, scene_id: str, *, allow_overwrite: bool = False) -> SceneDetailResult | None:
    """Detail a single scene and return the metadata.

    Returns:
        SceneDetailResult | None: Metadata for the targeted scene (None if skipped).
    """
    results = anyio.run(
        partial(
            _run_scene_mvp_async,
            project_path,
            scene_id=scene_id,
            allow_overwrite=allow_overwrite,
        )
    )
    return results.get(scene_id)
