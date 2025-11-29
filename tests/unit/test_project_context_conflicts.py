"""Conflict and delete coverage for ProjectContext operations."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from rentl_core.context.project import ProjectContext
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.glossary import GlossaryEntry
from rentl_core.model.line import SourceLine, SourceLineMeta, TranslatedLine
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneAnnotations, SceneMetadata


def _build_context(tmp_path: Path) -> ProjectContext:
    """Create a minimal ProjectContext with one of each entity type.

    Returns:
        ProjectContext: Initialized context ready for mutation tests.
    """
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    output_dir = tmp_path / "output"
    for directory in [metadata_dir, scenes_dir, context_docs_dir, output_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="test",
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
        route_ids=["route_1"],
        title="Test Scene",
        title_origin="human",
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
    character = CharacterMetadata(
        id="char_1",
        name_src="名前",
        name_src_origin="human",
        name_tgt=None,
        pronouns=None,
        notes=None,
    )
    location = LocationMetadata(
        id="loc_1",
        name_src="場所",
        name_src_origin="human",
        name_tgt=None,
        description=None,
    )
    route = RouteMetadata(
        id="route_1",
        name="Route",
        name_origin="human",
        scene_ids=["scene_1"],
        synopsis=None,
        synopsis_origin=None,
        primary_characters=[],
        primary_characters_origin=None,
    )

    # Seed a source line file so translation persistence works
    source_line = SourceLine(id="scene_1_0001", text="line", meta=SourceLineMeta())
    scene_file = scenes_dir / "scene_1.jsonl"
    scene_file.write_text(source_line.model_dump_json(exclude_none=True) + "\n")

    return ProjectContext(
        project_path=tmp_path,
        game=game,
        characters={character.id: character},
        glossary=[],
        locations={location.id: location},
        routes={route.id: route},
        scenes={scene.id: scene},
        metadata_dir=metadata_dir,
        scenes_dir=scenes_dir,
        context_docs_dir=context_docs_dir,
        output_dir=output_dir,
    )


@pytest.mark.anyio
async def test_translation_conflict_and_overwrite(tmp_path: Path) -> None:
    """record_translation should detect conflicts and allow overwrites."""
    context = _build_context(tmp_path)
    line = TranslatedLine(
        id="scene_1_0001",
        text_src="line",
        text_tgt="first",
        text_tgt_origin="agent:test",
    )

    msg = await context.record_translation("scene_1", line)
    assert "Stored translation" in msg

    # Recent update triggers conflict even with allow_overwrite
    context._recent_updates["translation", "scene_1", line.id] = time.time()
    conflict = await context.record_translation(
        "scene_1",
        TranslatedLine(id=line.id, text_src="line", text_tgt="second", text_tgt_origin="agent:test2"),
        allow_overwrite=True,
    )
    assert "CONCURRENT UPDATE DETECTED" in conflict

    # Older update allows overwrite
    context._recent_updates["translation", "scene_1", line.id] = time.time() - 100
    overwrite = await context.record_translation(
        "scene_1",
        TranslatedLine(id=line.id, text_src="line", text_tgt="second", text_tgt_origin="agent:test2"),
        allow_overwrite=True,
    )
    assert "Stored translation" in overwrite

    translations = await context.get_translations("scene_1")
    assert translations[0].text_tgt == "second"


@pytest.mark.anyio
async def test_route_conflict_detection(tmp_path: Path) -> None:
    """Route updates should surface conflict feedback on rapid repeats."""
    context = _build_context(tmp_path)

    ok = await context.update_route_synopsis("route_1", "first synopsis", "agent:route")
    assert "Successfully updated synopsis" in ok
    conflict = await context.update_route_synopsis("route_1", "second synopsis", "agent:route")
    assert "CONCURRENT UPDATE DETECTED" in conflict

    ok_chars = await context.update_route_characters("route_1", ["char_1"], "agent:route")
    assert "Successfully updated primary characters" in ok_chars
    conflict_chars = await context.update_route_characters("route_1", ["char_1", "extra"], "agent:route")
    assert "CONCURRENT UPDATE DETECTED" in conflict_chars


@pytest.mark.anyio
async def test_location_and_character_conflicts(tmp_path: Path) -> None:
    """Location and character updates should detect rapid consecutive writes."""
    context = _build_context(tmp_path)

    loc_ok = await context.update_location_description("loc_1", "desc", "agent:loc")
    assert "Successfully updated description" in loc_ok
    loc_conflict = await context.update_location_description("loc_1", "desc2", "agent:loc")
    assert "CONCURRENT UPDATE DETECTED" in loc_conflict

    char_ok = await context.update_character_notes("char_1", "notes", "agent:char")
    assert "Successfully updated notes" in char_ok
    char_conflict = await context.update_character_notes("char_1", "notes2", "agent:char")
    assert "CONCURRENT UPDATE DETECTED" in char_conflict


@pytest.mark.anyio
async def test_delete_glossary_entry(tmp_path: Path) -> None:
    """Deleting an existing glossary entry should succeed and remove it."""
    context = _build_context(tmp_path)
    entry = GlossaryEntry(
        term_src="term",
        term_src_origin="human",
        term_tgt="tgt",
        term_tgt_origin="human",
        notes="note",
        notes_origin="human",
    )
    context.glossary.append(entry)

    msg = await context.delete_glossary_entry("term")
    assert "Deleted glossary entry" in msg
    assert not context.glossary
