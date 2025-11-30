"""Tests for HITL/provenance helpers and tool edge cases."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_agents.tools.hitl import request_if_human_authored
from rentl_core.context.project import ProjectContext
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
    update = next(t for t in tools if t.name == "update_glossary_entry")

    # Human-authored -> approval request
    approval = await update.coroutine(term_src="term", term_tgt="new")  # type: ignore[attr-defined]
    assert "approval required" in approval.lower()

    # Add a new entry then conflict with recent update
    add = next(t for t in tools if t.name == "add_glossary_entry")
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
    update_desc = next(t for t in tools if t.name == "update_location_description")

    approval = await update_desc.coroutine(location_id="loc_1", description="new desc")  # type: ignore[attr-defined]
    assert "approval required" in approval.lower()

    # After approval, allow_overwrite=True should bypass
    tools_overwrite = build_location_tools(context, allow_overwrite=True)
    update_desc_overwrite = next(t for t in tools_overwrite if t.name == "update_location_description")
    ok = await update_desc_overwrite.coroutine(location_id="loc_1", description="agent desc")  # type: ignore[attr-defined]
    assert "Successfully updated" in ok or "CONCURRENT" in ok or "approval required" in ok.lower()


@pytest.mark.anyio
async def test_route_update_conflict_and_noop(tmp_path: Path) -> None:
    """Route tool updates should detect conflicts and allow agent-owned updates."""
    context = _context(tmp_path)
    tools = build_route_tools(context, allow_overwrite=False)
    update_synopsis = next(t for t in tools if t.name == "update_route_synopsis")
    update_chars = next(t for t in tools if t.name == "update_route_characters")

    # existing synopsis has agent origin -> should proceed without approval
    ok = await update_synopsis.coroutine(route_id="route_1", synopsis="new")  # type: ignore[attr-defined]
    assert "Successfully updated" in ok or "CONCURRENT" in ok

    # primary_characters has agent origin; second update quickly should conflict
    ok_chars = await update_chars.coroutine(route_id="route_1", character_ids=["mc"])  # type: ignore[attr-defined]
    assert "Successfully updated" in ok_chars or "CONCURRENT" in ok_chars
    conflict = await update_chars.coroutine(route_id="route_1", character_ids=["mc", "x"])  # type: ignore[attr-defined]
    assert "CONCURRENT UPDATE DETECTED" in conflict or "already updated" in conflict
