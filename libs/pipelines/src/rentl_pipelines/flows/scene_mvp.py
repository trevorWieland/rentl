"""Scene-level pipelines for summarization MVP."""

from __future__ import annotations

from functools import partial
from pathlib import Path

import anyio
from rentl_agents.graph.engine import summarize_scene
from rentl_core.context.project import load_project_context


async def _run_scene_mvp_async(
    project_path: Path,
    *,
    scene_id: str | None = None,
    allow_overwrite: bool = False,
) -> dict[str, str]:
    """Summarize all target scenes and return their summaries.

    Returns:
        dict[str, str]: Mapping of scene ids to generated summaries.
    """
    context = await load_project_context(project_path)
    target_ids = [scene_id] if scene_id else sorted(context.scenes.keys())
    results: dict[str, str] = {}

    for sid in target_ids:
        scene = context.get_scene(sid)
        if scene.annotations.summary and not allow_overwrite:
            continue
        summary = await summarize_scene(context, sid, allow_overwrite=allow_overwrite)
        results[sid] = summary

    return results


def run_scene_mvp(project_path: Path, *, allow_overwrite: bool = False) -> dict[str, str]:
    """Summarize every scene in *project_path* and return summaries.

    Returns:
        dict[str, str]: Mapping of scene ids to generated summaries.
    """
    return anyio.run(partial(_run_scene_mvp_async, project_path, allow_overwrite=allow_overwrite))


def run_scene_summary(project_path: Path, scene_id: str, *, allow_overwrite: bool = False) -> str:
    """Summarize a single scene and return the new summary.

    Returns:
        str: Summary text for the targeted scene (empty if skipped).
    """
    results = anyio.run(
        partial(
            _run_scene_mvp_async,
            project_path,
            scene_id=scene_id,
            allow_overwrite=allow_overwrite,
        )
    )
    return results.get(scene_id, "")
