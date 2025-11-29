"""High-level smoke tests for running all phases on tiny_vn with mocked agents."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from rentl_agents.subagents.glossary_curator import GlossaryDetailResult
from rentl_core.context.project import ProjectContext, load_project_context
from rentl_core.model.line import TranslatedLine
from rentl_pipelines.flows.context_builder import ContextBuilderResult, _run_context_builder_async
from rentl_pipelines.flows.editor import EditorResult, _run_editor_async
from rentl_pipelines.flows.translator import TranslatorResult, _run_translator_async


@pytest.mark.anyio
async def test_tiny_vn_full_pipeline_smoke(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Run context → translate → edit against tiny_vn with stubbed subagents."""
    project_path = tiny_vn_tmp

    async def detail_scene_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        await context.set_scene_summary(scene_id, f"Summary for {scene_id}", "agent:scene_detailer")
        await context.set_scene_tags(scene_id, ["tag1", "tag2"], "agent:scene_detailer")
        await context.set_scene_characters(scene_id, ["mc"], "agent:scene_detailer")
        await context.set_scene_locations(scene_id, ["school"], "agent:scene_detailer")

    async def detail_character_stub(context: ProjectContext, character_id: str, **_: object) -> None:
        await context.update_character_name_tgt(character_id, f"{character_id}-tgt", "agent:character_detailer")
        await context.update_character_pronouns(character_id, "they/them", "agent:character_detailer")
        await context.update_character_notes(character_id, "stub notes", "agent:character_detailer")

    async def detail_location_stub(context: ProjectContext, location_id: str, **_: object) -> None:
        await context.update_location_name_tgt(location_id, f"{location_id}-tgt", "agent:location_detailer")
        await context.update_location_description(location_id, "stub description", "agent:location_detailer")

    async def detail_route_stub(context: ProjectContext, route_id: str, **_: object) -> None:
        await context.update_route_synopsis(route_id, f"Synopsis for {route_id}", "agent:route_detailer")
        await context.update_route_characters(route_id, ["mc"], "agent:route_detailer")

    async def detail_glossary_stub(context: ProjectContext, **_: object) -> GlossaryDetailResult:
        await context.add_glossary_entry("term", "translation", "notes", "agent:glossary")
        return GlossaryDetailResult(entries_added=1, entries_updated=0, total_entries=1)

    async def translate_scene_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        lines = await context.load_scene_lines(scene_id)
        for line in lines:
            translated = TranslatedLine(
                id=line.id,
                text_src=line.text,
                text_tgt=f"{line.text}-tgt",
                text_tgt_origin=f"agent:translator:{date.today().isoformat()}",
            )
            await context.record_translation(scene_id, translated)

    async def style_check_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        translations = await context.get_translations(scene_id)
        if translations:
            await context.add_translation_check(scene_id, translations[0].id, "style_check", True, None, "agent:style")

    async def consistency_check_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        translations = await context.get_translations(scene_id)
        if translations:
            await context.add_translation_check(
                scene_id, translations[0].id, "consistency_check", True, None, "agent:consistency"
            )

    async def review_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        translations = await context.get_translations(scene_id)
        if translations:
            await context.add_translation_check(
                scene_id, translations[0].id, "translation_review", True, None, "agent:review"
            )

    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene", detail_scene_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_character", detail_character_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_location", detail_location_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_route", detail_route_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_glossary", detail_glossary_stub)
    monkeypatch.setattr("rentl_pipelines.flows.translator.translate_scene", translate_scene_stub)
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_style_checks", style_check_stub)
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_consistency_checks", consistency_check_stub)
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_translation_review", review_stub)

    context_result: ContextBuilderResult = await _run_context_builder_async(project_path, concurrency=1)
    translator_result: TranslatorResult = await _run_translator_async(project_path, concurrency=2)
    editor_result: EditorResult = await _run_editor_async(project_path, concurrency=2)

    assert context_result.scenes_detailed == 4
    assert translator_result.scenes_translated == 4
    assert editor_result.scenes_checked == 4
    assert editor_result.translation_progress >= 0.0
    assert editor_result.editing_progress >= 0.0
    assert isinstance(editor_result.route_issue_counts, dict)

    context = await load_project_context(project_path)
    translations = await context.get_translations("scene_a_00")
    assert translations, "Expected translations to be recorded for scene_a_00"
    first_line = translations[0]
    assert first_line.meta.checks.get("style_check") is not None
    assert (project_path / "output" / "translations" / "scene_a_00.jsonl").exists()
