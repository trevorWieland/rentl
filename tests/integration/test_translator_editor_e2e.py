"""End-to-end translator and editor pipeline tests with mocked agents."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver
from rentl_agents.subagents.scene_translator import SceneTranslationResult
from rentl_core.context.project import ProjectContext, load_project_context
from rentl_core.model.line import TranslatedLine
from rentl_pipelines.flows.editor import EditorResult, _run_editor_async
from rentl_pipelines.flows.translator import TranslatorResult, _run_translator_async


async def _translate_scene_stub(
    context: ProjectContext,
    scene_id: str,
    *,
    allow_overwrite: bool = False,
    **_: object,
) -> SceneTranslationResult:
    """Write translations for all lines without calling an LLM.

    Returns:
        SceneTranslationResult: Stubbed translation result for the scene.
    """
    lines = await context.load_scene_lines(scene_id)
    await context._load_translations(scene_id)
    for line in lines:
        translation = TranslatedLine.from_source(
            line,
            f"{line.text}-tgt",
            text_tgt_origin=f"agent:translator:{date.today().isoformat()}",
        )
        await context.record_translation(scene_id, translation, allow_overwrite=True)
    return SceneTranslationResult(scene_id=scene_id, lines_translated=len(lines))


async def _style_check_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
    translations = await context.get_translations(scene_id)
    for t in translations:
        await context.add_translation_check(
            scene_id,
            t.id,
            "style_check",
            True,
            "",
            f"agent:style:{date.today().isoformat()}",
        )


async def _consistency_check_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
    translations = await context.get_translations(scene_id)
    for t in translations:
        await context.add_translation_check(
            scene_id,
            t.id,
            "consistency_check",
            True,
            "",
            f"agent:consistency:{date.today().isoformat()}",
        )


async def _review_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
    translations = await context.get_translations(scene_id)
    for t in translations:
        await context.add_translation_check(
            scene_id,
            t.id,
            "translation_review",
            True,
            "",
            f"agent:review:{date.today().isoformat()}",
        )


@pytest.mark.anyio
async def test_translator_pipeline_e2e_with_mocks(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Run translator pipeline end-to-end with mocked translation agent."""
    project_path = tiny_vn_tmp
    monkeypatch.setattr("rentl_pipelines.flows.translator.translate_scene", _translate_scene_stub)

    result: TranslatorResult = await _run_translator_async(
        project_path,
        concurrency=2,
        checkpointer=MemorySaver(),
    )

    context = await load_project_context(project_path)
    for sid in context.scenes:
        translations = await context.get_translations(sid)
        assert translations, f"Expected translations for {sid}"
    assert result.scenes_translated == len(context.scenes)
    assert result.lines_translated > 0
    assert not result.errors
    assert result.scenes_skipped == 0


@pytest.mark.anyio
async def test_editor_pipeline_e2e_with_mocks(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Run editor pipeline end-to-end with mocked QA agents after translations exist."""
    project_path = tiny_vn_tmp

    # Seed translations using translator stub
    monkeypatch.setattr("rentl_pipelines.flows.translator.translate_scene", _translate_scene_stub)
    await _run_translator_async(project_path, concurrency=2, checkpointer=MemorySaver())

    # Patch editor QA runners
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_style_checks", _style_check_stub)
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_route_consistency_checks", _consistency_check_stub)
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_translation_review", _review_stub)

    result: EditorResult = await _run_editor_async(
        project_path,
        concurrency=2,
        checkpointer=MemorySaver(),
    )

    context = await load_project_context(project_path)
    for sid in context.scenes:
        translations = await context.get_translations(sid)
        assert translations, f"Expected translations for {sid}"
        assert all(t.meta.checks for t in translations), "Expected QA checks recorded"

    assert result.scenes_checked == len(context.scenes)
    assert result.report_path is not None
    assert result.route_issue_counts is not None
    assert not result.errors
