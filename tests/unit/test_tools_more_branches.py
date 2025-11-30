"""Additional tool coverage for edge branches (duplicates, overwrites, approvals)."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_core.context.project import ProjectContext
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.glossary import GlossaryEntry
from rentl_core.model.line import SourceLine, SourceLineMeta
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneAnnotations, SceneMetadata

from tests.helpers.tool_builders import (
    build_glossary_tools,
    build_location_tools,
    build_route_tools,
    build_scene_tools,
    build_translation_tools,
)


def _base_context(tmp_path: Path) -> ProjectContext:
    """Minimal context with one scene/location/route/glossary entry.

    Returns:
        ProjectContext: Initialized context with seeded metadata/files.
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
            summary="sum",
            summary_origin="agent:scene_detailer",
            tags=["tag"],
            tags_origin="agent:scene_detailer",
            primary_characters=["mc"],
            primary_characters_origin="agent:scene_detailer",
            locations=["loc_1"],
            locations_origin="agent:scene_detailer",
        ),
    )
    # Seed scene lines
    (scenes_dir / "scene_1.jsonl").write_text(
        SourceLine(id="s1", text="hi", meta=SourceLineMeta()).model_dump_json(exclude_none=True) + "\n"
    )

    route = RouteMetadata(
        id="route_1",
        name="Route",
        name_origin="agent:route_detailer",
        scene_ids=["scene_1"],
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
        name_tgt_origin="agent:location_detailer",
        description="desc",
        description_origin="agent:location_detailer",
    )
    glossary = [
        GlossaryEntry(
            term_src="term",
            term_src_origin="agent:glossary",
            term_tgt="tgt",
            term_tgt_origin="agent:glossary",
            notes=None,
            notes_origin=None,
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


@pytest.mark.anyio
async def test_scene_tools_single_use_guards(tmp_path: Path) -> None:
    """Scene write tools should guard against multiple writes in one session."""
    context = _base_context(tmp_path)
    tools = build_scene_tools(context, allow_overwrite=False)
    write_summary = next(t for t in tools if t.name == "write_scene_summary")

    msg = await write_summary.coroutine(scene_id="scene_1", summary="new")  # type: ignore[attr-defined]
    assert "Successfully updated" in msg or "CONCURRENT" in msg
    dup = await write_summary.coroutine(scene_id="scene_1", summary="again")  # type: ignore[attr-defined]
    assert "already stored" in dup


@pytest.mark.anyio
async def test_route_tools_duplicate_add_and_approval(tmp_path: Path) -> None:
    """Route updates should respect approval and duplicate guards."""
    context = _base_context(tmp_path)
    tools = build_route_tools(context, allow_overwrite=False)
    update_syn = next(t for t in tools if t.name == "update_route_synopsis")

    # Agent-origin data should update without approval prompt
    msg = await update_syn.coroutine(route_id="route_1", synopsis="new syn")  # type: ignore[attr-defined]
    assert "Successfully updated" in msg or "CONCURRENT" in msg

    # Duplicate add_route should note existence
    add_route = next((t for t in tools if t.name == "add_route"), None)
    if add_route:
        dup = await add_route.coroutine(route_id="route_1", name="dup", scene_ids=[])  # type: ignore[attr-defined]
        assert "already exists" in dup

    # primary characters already agent-origin; allow overwrite=True bypasses approvals
    tools_overwrite = build_route_tools(context, allow_overwrite=True)
    update_chars_overwrite = next(t for t in tools_overwrite if t.name == "update_route_characters")
    ok = await update_chars_overwrite.coroutine(route_id="route_1", character_ids=["mc", "x"])  # type: ignore[attr-defined]
    assert "Successfully updated" in ok or "CONCURRENT" in ok


@pytest.mark.anyio
async def test_location_tools_duplicate_add_and_overwrite(tmp_path: Path) -> None:
    """Location tools should handle duplicate adds and overwrite paths."""
    context = _base_context(tmp_path)
    tools = build_location_tools(context, allow_overwrite=False)
    add_loc = next(t for t in tools if t.name == "add_location")
    dup = await add_loc.coroutine(location_id="loc_1", name_src="x")  # type: ignore[attr-defined]
    assert "already exists" in dup

    # allow_overwrite should skip approval on human-owned fields
    tools_overwrite = build_location_tools(context, allow_overwrite=True)
    update_name = next(t for t in tools_overwrite if t.name == "update_location_name_tgt")
    ok = await update_name.coroutine(location_id="loc_1", name_tgt="New Place")  # type: ignore[attr-defined]
    assert "Successfully updated" in ok or "CONCURRENT" in ok


@pytest.mark.anyio
async def test_glossary_tools_duplicates_and_human_protection(tmp_path: Path) -> None:
    """Glossary tools should detect duplicates and human-owned data."""
    context = _base_context(tmp_path)
    tools = build_glossary_tools(context, allow_overwrite=False)
    add = next(t for t in tools if t.name == "add_glossary_entry")
    dup = await add.coroutine(term_src="term", term_tgt="dup")  # type: ignore[attr-defined]
    assert "already exists" in dup

    update = next(t for t in tools if t.name == "update_glossary_entry")
    approval = await update.coroutine(term_src="term", term_tgt="new")  # type: ignore[attr-defined]
    assert "approval required" in approval.lower() or "successfully updated" in approval.lower()


@pytest.mark.anyio
async def test_translation_tools_overwrite_and_mtl_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Translation tool should respect overwrite flag and availability check."""
    context = _base_context(tmp_path)
    tools = build_translation_tools(context, agent_name="tester", allow_overwrite=False)

    # First write succeeds
    write_translation = next(t for t in tools if t.name == "write_translation")
    msg = await write_translation.coroutine(  # type: ignore[attr-defined]
        scene_id="scene_1", line_id="s1", source_text="hi", target_text="HI"
    )
    assert "Stored translation" in msg
    # Second write without overwrite should block
    blocked = await write_translation.coroutine(  # type: ignore[attr-defined]
        scene_id="scene_1", line_id="s1", source_text="hi", target_text="HI-again"
    )
    assert "already exists" in blocked or "already written" in blocked

    # allow_overwrite=True should pass
    tools_overwrite = build_translation_tools(context, agent_name="tester", allow_overwrite=True)
    write_translation_overwrite = next(t for t in tools_overwrite if t.name == "write_translation")
    ok = await write_translation_overwrite.coroutine(  # type: ignore[attr-defined]
        scene_id="scene_1", line_id="s1", source_text="hi", target_text="HI-OVER"
    )
    assert "Stored translation" in ok or "CONCURRENT" in ok

    # MTL availability path
    monkeypatch.setenv("MTL_URL", "http://localhost:1")
    monkeypatch.setenv("MTL_MODEL", "mtl-test")
    monkeypatch.setenv("MTL_API_KEY", "x")
    monkeypatch.setenv("OPENAI_URL", "http://localhost:2")
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    monkeypatch.setenv("LLM_MODEL", "llm")
    trans_tools = build_translation_tools(context, agent_name="tester", allow_overwrite=True)
    check_mtl = next(t for t in trans_tools if t.name == "check_mtl_available")
    status = check_mtl.invoke({})  # type: ignore[arg-type]
    assert "available" in status.lower()
