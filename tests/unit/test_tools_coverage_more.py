"""Additional coverage for tool provenance, conflicts, deletes, and stats."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.tools import BaseTool
from rentl_agents.tools.character import build_character_tools
from rentl_agents.tools.glossary import build_glossary_tools
from rentl_agents.tools.location import build_location_tools
from rentl_agents.tools.qa import build_qa_tools
from rentl_agents.tools.route import build_route_tools
from rentl_agents.tools.scene import build_scene_tools
from rentl_agents.tools.stats import build_stats_tools
from rentl_agents.tools.translation import build_translation_tools
from rentl_core.context.project import load_project_context
from rentl_core.model.line import TranslatedLine


def _find_tool(tools: list, name: str) -> BaseTool:
    return next(tool for tool in tools if getattr(tool, "name", "") == name)


@pytest.mark.anyio
async def test_character_location_route_glossary_tools_request_approval(tiny_vn_tmp: Path) -> None:
    """Ensure tools surface approvals for human-authored fields."""
    context = await load_project_context(tiny_vn_tmp)

    # Character pronouns human-authored -> approval required
    context.characters["mc"].pronouns = "they/them"
    context.characters["mc"].pronouns_origin = "human"
    char_tools = build_character_tools(context)
    update_pronouns = _find_tool(char_tools, "update_character_pronouns")
    msg = await update_pronouns.coroutine(character_id="mc", pronouns="he/him")  # type: ignore[attr-defined]
    assert "APPROVAL REQUIRED" in msg

    # Location description human-authored -> approval required
    context.locations["classroom"].description = "desc"
    context.locations["classroom"].description_origin = "human"
    loc_tools = build_location_tools(context)
    update_desc = _find_tool(loc_tools, "update_location_description")
    loc_msg = await update_desc.coroutine(location_id="classroom", description="new desc")  # type: ignore[attr-defined]
    assert "APPROVAL REQUIRED" in loc_msg

    # Route synopsis human-authored -> approval required
    context.routes["common"].synopsis = "syn"
    context.routes["common"].synopsis_origin = "human"
    route_tools = build_route_tools(context)
    update_synopsis = _find_tool(route_tools, "update_route_synopsis")
    route_msg = await update_synopsis.coroutine(route_id="common", synopsis="updated")  # type: ignore[attr-defined]
    assert "APPROVAL REQUIRED" in route_msg

    # Glossary update with human origin -> approval required
    await context.add_glossary_entry("term", "tgt", "notes", "human")
    glossary_tools = build_glossary_tools(context)
    update_glossary = _find_tool(glossary_tools, "update_glossary_entry")
    gloss_msg = await update_glossary.coroutine(term_src="term", term_tgt="new", notes="n")  # type: ignore[attr-defined]
    assert "APPROVAL REQUIRED" in gloss_msg

    # Glossary delete should remove entry
    delete_glossary = _find_tool(glossary_tools, "delete_glossary_entry")
    delete_msg = await delete_glossary.coroutine(term_src="term")  # type: ignore[attr-defined]
    assert "Deleted glossary entry" in delete_msg

    # Scene tools: human-authored summary should request approval, duplicate calls guarded
    scene_tools = build_scene_tools(context)
    scene_id = "scene_a_00"
    context.scenes[scene_id].annotations.summary = "human summary"
    context.scenes[scene_id].annotations.summary_origin = "human"
    write_summary = _find_tool(scene_tools, "write_scene_summary")
    approval_msg = await write_summary.coroutine(scene_id=scene_id, summary="new summary")  # type: ignore[attr-defined]
    assert "APPROVAL REQUIRED" in approval_msg

    # Allow overwrite when agent-authored
    context.scenes[scene_id].annotations.summary_origin = "agent:test"
    ok_msg = await write_summary.coroutine(scene_id=scene_id, summary="agent summary")  # type: ignore[attr-defined]
    assert "Successfully updated" in ok_msg or "Summary already" in ok_msg
    repeat_msg = await write_summary.coroutine(scene_id=scene_id, summary="agent summary")  # type: ignore[attr-defined]
    assert "already stored" in repeat_msg


@pytest.mark.anyio
async def test_translation_and_stats_tools(tiny_vn_tmp: Path) -> None:
    """Write translations via tool and surface stats/QA checks."""
    context = await load_project_context(tiny_vn_tmp)
    scene_id = "scene_a_00"
    line = (await context.load_scene_lines(scene_id))[0]

    # Translation tool writes without approval when empty
    trans_tools = build_translation_tools(context, agent_name="unit_test", allow_overwrite=False)
    write_translation = _find_tool(trans_tools, "write_translation")
    write_msg = await write_translation.coroutine(  # type: ignore[attr-defined]
        scene_id=scene_id, line_id=line.id, source_text=line.text, target_text="translated"
    )
    assert "Stored translation" in write_msg or "Recorded" in write_msg or "Successfully" in write_msg

    # Stats tool should reflect translated lines
    stats_tools = build_stats_tools(context)
    get_progress = _find_tool(stats_tools, "get_translation_progress")
    progress = await get_progress.coroutine(scene_id=scene_id)  # type: ignore[attr-defined]
    assert "lines translated" in progress

    # QA tools should record checks on translated line
    translations = await context.get_translations(scene_id)
    assert translations, "Expected translation to be recorded"
    tline: TranslatedLine = translations[0]
    qa_tools = build_qa_tools(context)
    record_style_check = _find_tool(qa_tools, "record_style_check")
    record_consistency_check = _find_tool(qa_tools, "record_consistency_check")
    record_translation_review = _find_tool(qa_tools, "record_translation_review")
    await record_style_check.coroutine(scene_id=scene_id, line_id=tline.id, passed=True, note="ok")  # type: ignore[attr-defined]
    await record_consistency_check.coroutine(scene_id=scene_id, line_id=tline.id, passed=True, note="ok")  # type: ignore[attr-defined]
    await record_translation_review.coroutine(scene_id=scene_id, line_id=tline.id, passed=True, note="ok")  # type: ignore[attr-defined]
    updated = await context.get_translations(scene_id)
    assert updated[0].meta.checks, "Expected QA checks to be stored"
