"""HITL coverage for scene tools when overwriting human-authored data."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import anyio
import pytest
from rentl_agents.tools.scene import build_scene_tools
from rentl_core.context.project import ProjectContext
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.scene import SceneAnnotations, SceneMetadata


@pytest.mark.anyio
async def test_write_scene_summary_requests_approval_for_human(tmp_path: Path) -> None:
    """Overwriting human-authored summary should request approval and not change data."""
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    output_dir = tmp_path / "output"
    context_docs_dir = metadata_dir / "context_docs"
    for d in (metadata_dir, scenes_dir, context_docs_dir, output_dir):
        await anyio.Path(d).mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="t",
        title_origin="human",
        description="",
        description_origin="human",
        source_lang="spa",
        target_lang="eng",
        genres=[],
        genres_origin="human",
        synopsis="",
        synopsis_origin="human",
        timeline=[],
        ui=UIConstraints(max_line_length=42),
    )
    annotations = SceneAnnotations(summary="humana", summary_origin="human")
    scene = SceneMetadata(id="scene_1", route_ids=[], title=None, title_origin=None, annotations=annotations)
    context = ProjectContext(
        project_path=tmp_path,
        game=game,
        characters={},
        glossary=[],
        locations={},
        routes={},
        scenes={scene.id: scene},
        metadata_dir=metadata_dir,
        scenes_dir=scenes_dir,
        context_docs_dir=context_docs_dir,
        output_dir=output_dir,
    )

    tools = build_scene_tools(context, allow_overwrite=False)
    write_summary = next(tool for tool in tools if getattr(tool, "name", "") == "write_scene_summary")

    result = await write_summary.ainvoke({"scene_id": scene.id, "summary": "nueva"})
    assert "APPROVAL REQUIRED" in result
    assert context.get_scene(scene.id).annotations.summary == "humana"


@pytest.mark.anyio
async def test_write_scene_summary_allows_agent_origin(tmp_path: Path) -> None:
    """Non-human origin can be overwritten without approval."""
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    output_dir = tmp_path / "output"
    context_docs_dir = metadata_dir / "context_docs"
    for d in (metadata_dir, scenes_dir, context_docs_dir, output_dir):
        await anyio.Path(d).mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="t",
        title_origin="human",
        description="",
        description_origin="human",
        source_lang="spa",
        target_lang="eng",
        genres=[],
        genres_origin="human",
        synopsis="",
        synopsis_origin="human",
        timeline=[],
        ui=UIConstraints(max_line_length=42),
    )
    annotations = SceneAnnotations(summary="agent old", summary_origin="agent:scene_detailer")
    scene = SceneMetadata(id="scene_1", route_ids=[], title=None, title_origin=None, annotations=annotations)
    context = ProjectContext(
        project_path=tmp_path,
        game=game,
        characters={},
        glossary=[],
        locations={},
        routes={},
        scenes={scene.id: scene},
        metadata_dir=metadata_dir,
        scenes_dir=scenes_dir,
        context_docs_dir=context_docs_dir,
        output_dir=output_dir,
    )

    tools = build_scene_tools(context, allow_overwrite=False)
    write_summary = next(tool for tool in tools if getattr(tool, "name", "") == "write_scene_summary")

    new_summary = f"actualizado {date.today().isoformat()}"
    result = await write_summary.ainvoke({"scene_id": scene.id, "summary": new_summary})
    assert "APPROVAL REQUIRED" not in result
    assert context.get_scene(scene.id).annotations.summary == new_summary
