"""Unit tests for ProjectContext translation persistence and QA checks."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from rentl_core.context.project import ProjectContext
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.line import SourceLine, SourceLineMeta, TranslatedLine
from rentl_core.model.scene import SceneAnnotations, SceneMetadata


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"], indirect=True)
async def test_record_translation_and_checks(tmp_path: Path) -> None:
    """Translations should persist to disk and accept QA checks with conflicts handled."""
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    output_dir = tmp_path / "output"
    for directory in [metadata_dir, scenes_dir, context_docs_dir, output_dir]:
        await anyio.Path(directory).mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="test",
        title_origin="test",
        description="",
        description_origin="test",
        source_lang="jpn",
        target_lang="eng",
        genres=[],
        genres_origin="test",
        synopsis="",
        synopsis_origin="test",
        timeline=[],
        ui=UIConstraints(max_line_length=42),
    )
    scene = SceneMetadata(
        id="scene_1",
        route_ids=[],
        title="Test Scene",
        title_origin="test",
        annotations=SceneAnnotations(
            summary=None,
            summary_origin=None,
            tags=[],
            tags_origin=None,
            primary_characters=[],
            primary_characters_origin=None,
            locations=[],
            locations_origin=None,
        ),
    )
    # Minimal required collections
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

    # Seed a source line file
    source_line = SourceLine(
        id="scene_1_0001",
        text="おはよう",
        meta=SourceLineMeta(),
    )
    scene_file = scenes_dir / f"{scene.id}.jsonl"
    async with await anyio.open_file(scene_file, "w", encoding="utf-8") as stream:
        await stream.write(source_line.model_dump_json(exclude_none=True) + "\n")

    translated = TranslatedLine(
        id=source_line.id,
        text_src=source_line.text,
        text_tgt="Good morning",
        text_tgt_origin="agent:test",
    )

    # Record translation
    msg = await context.record_translation(scene.id, translated)
    assert "Stored translation" in msg

    # Record QA check
    check_msg = await context.add_translation_check(
        scene.id,
        source_line.id,
        "style_check",
        passed=True,
        note="ok",
        origin="agent:qa",
    )
    assert "Recorded style_check" in check_msg

    # Ensure translation persisted
    translations = await context.get_translations(scene.id)
    assert len(translations) == 1
    assert translations[0].meta.checks["style_check"] == (True, "ok")
