"""Unit tests for translation and QA tools."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from rentl_agents.tools.translation import build_translation_tools
from rentl_core.context.project import ProjectContext
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.line import SourceLine, SourceLineMeta, TranslatedLine
from rentl_core.model.scene import SceneAnnotations, SceneMetadata


@pytest.mark.anyio
async def test_write_translation_respects_existing_human_origin(tmp_path: Path) -> None:
    """write_translation should request approval when overwriting human-authored translations."""
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    output_dir = tmp_path / "output"
    for directory in (metadata_dir, scenes_dir, context_docs_dir, output_dir):
        await anyio.Path(directory).mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="t",
        title_origin="human",
        description="",
        description_origin="human",
        source_lang="jpn",
        target_lang="eng",
        genres=[],
        genres_origin="human",
        synopsis="",
        synopsis_origin="human",
        timeline=[],
        ui=UIConstraints(max_line_length=42),
    )
    scene = SceneMetadata(
        id="scene_1",
        route_ids=[],
        title=None,
        title_origin=None,
        annotations=SceneAnnotations(),
    )
    line = SourceLine(id="scene_1_0001", text="こんにちは", meta=SourceLineMeta())
    scene_path = scenes_dir / "scene_1.jsonl"
    async with await anyio.open_file(scene_path, "w", encoding="utf-8") as stream:
        await stream.write(line.model_dump_json(exclude_none=True) + "\n")

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

    # Seed an existing human translation.
    existing = TranslatedLine(
        id=line.id,
        text_src=line.text,
        text_tgt="Hello",
        text_tgt_origin="human",
    )
    await context.record_translation(scene.id, existing)

    tools = build_translation_tools(context, allow_overwrite=False)
    write_translation = next(tool for tool in tools if getattr(tool, "name", "") == "write_translation")

    result = await write_translation.ainvoke(
        {"scene_id": scene.id, "line_id": line.id, "source_text": line.text, "target_text": "Hi"}
    )
    assert "APPROVAL REQUIRED" in result


@pytest.mark.anyio
async def test_read_scene_returns_transcript(tmp_path: Path) -> None:
    """read_scene should surface line ids and speakers for translators."""
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    output_dir = tmp_path / "output"
    for directory in (metadata_dir, scenes_dir, context_docs_dir, output_dir):
        await anyio.Path(directory).mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="t",
        title_origin="human",
        description="",
        description_origin="human",
        source_lang="jpn",
        target_lang="eng",
        genres=[],
        genres_origin="human",
        synopsis="",
        synopsis_origin="human",
        timeline=[],
        ui=UIConstraints(max_line_length=42),
    )
    scene = SceneMetadata(
        id="scene_1",
        route_ids=[],
        title="Intro",
        title_origin="human",
        annotations=SceneAnnotations(primary_characters=["mc"], primary_characters_origin="human"),
    )
    line = SourceLine(id="scene_1_0001", text="こんにちは", meta=SourceLineMeta(speaker="MC", speaker_origin="human"))
    scene_path = scenes_dir / "scene_1.jsonl"
    async with await anyio.open_file(scene_path, "w", encoding="utf-8") as stream:
        await stream.write(line.model_dump_json(exclude_none=True) + "\n")

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

    tools = build_translation_tools(context, allow_overwrite=False)
    read_scene = next(tool for tool in tools if getattr(tool, "name", "") == "read_scene")
    transcript = await read_scene.ainvoke({"scene_id": scene.id})
    assert "scene_1_0001" in transcript
    assert "MC" in transcript
    assert "こんにちは" in transcript
