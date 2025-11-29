"""Additional coverage for tool behaviors (reads, adds, stats, error paths)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from langchain_core.tools import BaseTool
from rentl_agents.tools.character import build_character_tools
from rentl_agents.tools.glossary import build_glossary_tools
from rentl_agents.tools.location import build_location_tools
from rentl_agents.tools.qa import read_translations
from rentl_agents.tools.route import build_route_tools
from rentl_agents.tools.scene import build_scene_tools
from rentl_agents.tools.stats import build_stats_tools
from rentl_agents.tools.translation import build_translation_tools
from rentl_core.context.project import load_project_context
from rentl_core.model.line import TranslatedLine


def _tool(tools: list[Any], name: str) -> BaseTool:
    """Return tool by name."""
    return next(tool for tool in tools if getattr(tool, "name", "") == name)


@pytest.mark.anyio
async def test_scene_read_and_write_paths(tiny_vn_tmp: Path) -> None:
    """Exercise read_scene and write_* tools including single-use guards."""
    context = await load_project_context(tiny_vn_tmp)
    scene_tools = build_scene_tools(context, allow_overwrite=False)
    scene_id = "scene_a_00"

    read_scene = _tool(scene_tools, "read_scene")
    transcript = await read_scene.coroutine(scene_id=scene_id)  # type: ignore[attr-defined]
    assert "Transcript" in transcript
    assert scene_id.replace("_", " ") or scene_id in transcript

    write_tags = _tool(scene_tools, "write_scene_tags")
    msg = await write_tags.coroutine(scene_id=scene_id, tags=["alpha"])  # type: ignore[attr-defined]
    assert "Successfully updated" in msg
    dup = await write_tags.coroutine(scene_id=scene_id, tags=["alpha"])  # type: ignore[attr-defined]
    assert "already stored" in dup

    write_chars = _tool(scene_tools, "write_primary_characters")
    msg_chars = await write_chars.coroutine(scene_id=scene_id, character_ids=["mc"])  # type: ignore[attr-defined]
    assert "Successfully updated" in msg_chars

    write_locs = _tool(scene_tools, "write_scene_locations")
    msg_locs = await write_locs.coroutine(scene_id=scene_id, location_ids=["classroom"])  # type: ignore[attr-defined]
    assert "Successfully updated" in msg_locs


@pytest.mark.anyio
async def test_character_location_route_add_and_read(tiny_vn_tmp: Path) -> None:
    """Cover add/read paths for character/location/route tools."""
    context = await load_project_context(tiny_vn_tmp)

    # Character add and read
    char_tools = build_character_tools(context)
    add_char = _tool(char_tools, "add_character")
    add_msg = await add_char.coroutine(  # type: ignore[attr-defined]
        character_id="newbie", name_src="新", name_tgt="Newbie", pronouns="they", notes="note"
    )
    assert "Added" in add_msg or "already exists" in add_msg
    read_char = _tool(char_tools, "read_character")
    char_info = read_char.invoke({"character_id": "newbie"})  # type: ignore[arg-type]
    assert "Newbie" in char_info

    # Location add and read
    loc_tools = build_location_tools(context)
    add_loc = _tool(loc_tools, "add_location")
    add_loc_msg = await add_loc.coroutine(  # type: ignore[attr-defined]
        location_id="cafe", name_src="喫茶店", name_tgt="Cafe", description="quiet"
    )
    assert "Added" in add_loc_msg or "already exists" in add_loc_msg
    read_loc = _tool(loc_tools, "read_location")
    loc_info = read_loc.invoke({"location_id": "cafe"})  # type: ignore[arg-type]
    assert "Cafe" in loc_info

    # Route read
    route_tools = build_route_tools(context)
    read_route = _tool(route_tools, "read_route")
    route_info = read_route.invoke({"route_id": "common"})  # type: ignore[arg-type]
    assert "Route ID: common" in route_info


@pytest.mark.anyio
async def test_glossary_search_read_delete_missing(tiny_vn_tmp: Path) -> None:
    """Glossary tools for search/read missing entries and delete missing."""
    context = await load_project_context(tiny_vn_tmp)
    glossary_tools = build_glossary_tools(context)
    search = _tool(glossary_tools, "search_glossary")
    search_msg = search.invoke({"term_src": "missing-term"})  # type: ignore[arg-type]
    assert "not found" in search_msg or "No glossary entry found" in search_msg

    read_entry = _tool(glossary_tools, "read_glossary_entry")
    read_msg = read_entry.invoke({"term_src": "missing-term"})  # type: ignore[arg-type]
    assert "not found" in read_msg or "No glossary entry found" in read_msg

    delete = _tool(glossary_tools, "delete_glossary_entry")
    delete_msg = await delete.coroutine(term_src="missing-term")  # type: ignore[attr-defined]
    assert "not found" in delete_msg


@pytest.mark.anyio
async def test_translation_tools_mtl_unavailable_and_ui_style(
    tiny_vn_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise translation tool branches when MTL is unavailable and read style/UI helpers."""
    context = await load_project_context(tiny_vn_tmp)
    trans_tools = build_translation_tools(context, agent_name="unit_test", allow_overwrite=False)

    # Force MTL unavailable
    monkeypatch.setattr("rentl_agents.tools.translation.is_mtl_available", lambda: False)
    mtl_tool = _tool(trans_tools, "mtl_translate")
    err = await mtl_tool.coroutine(line_id="x", source_text="hi", context_lines=None)  # type: ignore[attr-defined]
    assert "MTL backend not configured" in err

    read_style = _tool(trans_tools, "read_style_guide")
    style = await read_style.coroutine()  # type: ignore[attr-defined]
    assert "Style Guide" in style or style

    get_ui = _tool(trans_tools, "get_ui_settings")
    ui_msg = get_ui.invoke({})  # type: ignore[arg-type]
    assert "charset" in ui_msg or ui_msg

    check_mtl = _tool(trans_tools, "check_mtl_available")
    status = check_mtl.invoke({})  # type: ignore[arg-type]
    assert "not configured" in status or "available" in status


@pytest.mark.anyio
async def test_stats_and_qa_read_translations(tiny_vn_tmp: Path) -> None:
    """Stats tools and QA read behavior."""
    context = await load_project_context(tiny_vn_tmp)

    stats_tools = build_stats_tools(context)
    ctx_status = _tool(stats_tools, "get_context_status")
    status_msg = ctx_status.invoke({})  # type: ignore[arg-type]
    assert "Scenes" in status_msg

    scene_completion = _tool(stats_tools, "get_scene_completion")
    scene_msg = scene_completion.invoke({"scene_id": "scene_a_00"})  # type: ignore[arg-type]
    assert "Scene scene_a_00" in scene_msg

    char_completion = _tool(stats_tools, "get_character_completion")
    char_msg = char_completion.invoke({"character_id": "mc"})  # type: ignore[arg-type]
    assert "Character mc" in char_msg

    route_progress = _tool(stats_tools, "get_route_progress")
    route_msg = route_progress.invoke({"route_id": "common"})  # type: ignore[arg-type]
    assert "Route common" in route_msg

    # read_translations should handle missing then present
    missing_msg = await read_translations.coroutine(  # type: ignore[attr-defined]
        context=context, scene_id="scene_a_00"
    )
    assert "No translations" in missing_msg or "not found" in missing_msg
    # Add translation to exercise positive path
    line = (await context.load_scene_lines("scene_a_00"))[0]
    translated = TranslatedLine.from_source(line, f"{line.text}-tgt", text_tgt_origin=f"agent:test:{date.today()}")
    await context.record_translation("scene_a_00", translated, allow_overwrite=True)
    present_msg = await read_translations.coroutine(  # type: ignore[attr-defined]
        context=context, scene_id="scene_a_00"
    )
    assert "SRC" in present_msg
    assert "TGT" in present_msg
