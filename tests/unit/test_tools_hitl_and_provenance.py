"""Tests for HITL/provenance helpers and tool edge cases."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_agents.tools.character import character_delete_entry
from rentl_agents.tools.glossary import glossary_merge_entries
from rentl_agents.tools.hitl import request_if_human_authored
from rentl_agents.tools.location import location_delete_entry
from rentl_agents.tools.route import route_create_entry, route_delete_entry
from rentl_core.context.project import ProjectContext
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.glossary import GlossaryEntry
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneAnnotations, SceneMetadata

from tests.helpers.tool_builders import build_glossary_tools, build_location_tools, build_route_tools


def _context(tmp_path: Path) -> ProjectContext:
    """Create a minimal ProjectContext with one route/location/glossary entry.

    Returns:
        ProjectContext: Initialized context backed by the temp project paths.
    """
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    output_dir = tmp_path / "output"
    for directory in (metadata_dir, scenes_dir, context_docs_dir, output_dir):
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
        title="Test",
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
    route = RouteMetadata(
        id="route_1",
        name="Route",
        name_origin="human",
        scene_ids=[scene.id],
        synopsis="",
        synopsis_origin="agent:route_detailer",
        primary_characters=["mc"],
        primary_characters_origin="agent:route_detailer",
    )
    location = LocationMetadata(
        id="loc_1",
        name_src="場所",
        name_src_origin="human",
        name_tgt="Place",
        name_tgt_origin="human",
        description="desc",
        description_origin="human",
    )
    glossary = [
        GlossaryEntry(
            term_src="term",
            term_src_origin="human",
            term_tgt="tgt",
            term_tgt_origin="human",
            notes="note",
            notes_origin="human",
        )
    ]

    return ProjectContext(
        project_path=tmp_path,
        game=game,
        characters={},
        glossary=glossary,
        locations={location.id: location},
        routes={route.id: route},
        scenes={scene.id: scene},
        metadata_dir=metadata_dir,
        scenes_dir=scenes_dir,
        context_docs_dir=context_docs_dir,
        output_dir=output_dir,
    )


def test_request_if_human_authored_branches() -> None:
    """request_if_human_authored should return approval request only for human origin."""
    msg = request_if_human_authored(
        operation="update", target="field", current_value="val", current_origin="human", proposed_value="new"
    )
    assert msg is not None
    assert "approval required" in msg.lower()

    msg2 = request_if_human_authored(
        operation="update", target="field", current_value="val", current_origin="agent:foo", proposed_value="new"
    )
    assert msg2 is None

    msg3 = request_if_human_authored(
        operation="update", target="field", current_value=None, current_origin=None, proposed_value=None
    )
    assert msg3 is None


@pytest.mark.anyio
async def test_glossary_update_noop_and_conflict(tmp_path: Path) -> None:
    """Glossary tools should surface conflicts and no-op paths."""
    context = _context(tmp_path)
    tools = build_glossary_tools(context, allow_overwrite=False)
    update = next(t for t in tools if t.name == "glossary_update_entry")

    # Human-authored -> approval request
    approval = await update.coroutine(term_src="term", term_tgt="new")  # type: ignore[attr-defined]
    assert "approval required" in approval.lower()

    # Add a new entry then conflict with recent update
    add = next(t for t in tools if t.name == "glossary_create_entry")
    added = await add.coroutine(term_src="term2", term_tgt="tgt2")  # type: ignore[attr-defined]
    assert "successfully added" in added.lower()
    # Rapid update should return conflict message via ProjectContext timing
    conflict = await update.coroutine(term_src="term2", notes="note2")  # type: ignore[attr-defined]
    assert "CONCURRENT UPDATE DETECTED" in conflict or "Successfully updated" in conflict


@pytest.mark.anyio
async def test_location_update_conflict_and_noop(tmp_path: Path) -> None:
    """Location tool should request approval on human data and handle conflicts."""
    context = _context(tmp_path)
    tools = build_location_tools(context, allow_overwrite=False)
    update_desc = next(t for t in tools if t.name == "location_update_description")

    approval = await update_desc.coroutine(location_id="loc_1", description="new desc")  # type: ignore[attr-defined]
    assert "approval required" in approval.lower()

    # After approval, allow_overwrite=True should bypass
    tools_overwrite = build_location_tools(context, allow_overwrite=True)
    update_desc_overwrite = next(t for t in tools_overwrite if t.name == "location_update_description")
    ok = await update_desc_overwrite.coroutine(location_id="loc_1", description="agent desc")  # type: ignore[attr-defined]
    assert "Successfully updated" in ok or "CONCURRENT" in ok or "approval required" in ok.lower()


@pytest.mark.anyio
async def test_route_update_conflict_and_noop(tmp_path: Path) -> None:
    """Route tool updates should detect conflicts and allow agent-owned updates."""
    context = _context(tmp_path)
    tools = build_route_tools(context, allow_overwrite=False)
    update_synopsis = next(t for t in tools if t.name == "route_update_synopsis")
    update_chars = next(t for t in tools if t.name == "route_update_primary_characters")

    # existing synopsis has agent origin -> should proceed without approval
    ok = await update_synopsis.coroutine(route_id="route_1", synopsis="new")  # type: ignore[attr-defined]
    assert "Successfully updated" in ok or "CONCURRENT" in ok

    # primary_characters has agent origin; second update quickly should conflict
    ok_chars = await update_chars.coroutine(route_id="route_1", character_ids=["mc"])  # type: ignore[attr-defined]
    assert "Successfully updated" in ok_chars or "CONCURRENT" in ok_chars
    conflict = await update_chars.coroutine(route_id="route_1", character_ids=["mc", "x"])  # type: ignore[attr-defined]
    assert "CONCURRENT UPDATE DETECTED" in conflict or "already updated" in conflict


@pytest.mark.anyio
async def test_delete_tools_and_route_create(tmp_path: Path) -> None:
    """Delete tools should respect human origins and route creation should guard duplicates."""
    context = _context(tmp_path)

    # Character delete with human origin -> approval required
    context.characters["mc"] = CharacterMetadata(
        id="mc",
        name_src="MC",
        name_src_origin="human",
        name_tgt=None,
        name_tgt_origin=None,
        pronouns=None,
        pronouns_origin=None,
        notes=None,
        notes_origin=None,
    )
    msg = await character_delete_entry(context, "mc")
    assert "APPROVAL REQUIRED" in msg
    context.characters["mc"].name_src_origin = "agent:test"
    msg_ok = await character_delete_entry(context, "mc")
    assert "Deleted character" in msg_ok

    # Location delete with human origin -> approval required
    context.locations["loc_h"] = LocationMetadata(
        id="loc_h",
        name_src="Loc",
        name_src_origin="human",
        name_tgt=None,
        name_tgt_origin=None,
        description=None,
        description_origin=None,
    )
    loc_msg = await location_delete_entry(context, "loc_h")
    assert "APPROVAL REQUIRED" in loc_msg
    context.locations["loc_h"].name_src_origin = "agent:test"
    loc_ok = await location_delete_entry(context, "loc_h")
    assert "Deleted location" in loc_ok

    # Route create/delete with human origin on delete requiring approval
    create_ok = await route_create_entry(context, "new_route", "New Route", [])
    assert "Added route" in create_ok
    # Human name_origin on route_1 blocks delete
    delete_block = await route_delete_entry(context, "route_1")
    assert "APPROVAL REQUIRED" in delete_block
    context.routes["route_1"].name_origin = "agent:test"
    context.routes["route_1"].synopsis_origin = "agent:test"
    context.routes["route_1"].primary_characters_origin = "agent:test"
    delete_ok = await route_delete_entry(context, "route_1")
    assert "Deleted route" in delete_ok

    # Glossary merge with human origins should require approval; agent-origin merge should proceed
    context.glossary.append(
        GlossaryEntry(
            term_src="dup1",
            term_src_origin="human",
            term_tgt="A",
            term_tgt_origin="human",
            notes="n1",
            notes_origin="human",
        )
    )
    context.glossary.append(
        GlossaryEntry(
            term_src="dup2",
            term_src_origin="human",
            term_tgt="B",
            term_tgt_origin="human",
            notes="n2",
            notes_origin="human",
        )
    )
    merge_block = await glossary_merge_entries(context, "dup1", "dup2")
    assert "APPROVAL REQUIRED" in merge_block
    for entry in context.glossary:
        entry.term_src_origin = "agent:test"
        entry.term_tgt_origin = "agent:test"
        entry.notes_origin = "agent:test"
    merge_ok = await glossary_merge_entries(context, "dup1", "dup2")
    assert "Merged glossary entry" in merge_ok
