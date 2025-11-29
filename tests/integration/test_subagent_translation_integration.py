"""Integration tests for translator and reviewer subagents with mocked LLM behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_agents.subagents.translate_scene import translate_scene
from rentl_agents.subagents.translation_reviewer import run_translation_review
from rentl_core.context.project import ProjectContext, load_project_context
from rentl_core.model.line import TranslatedLine


@pytest.mark.anyio
async def test_translate_scene_records_translations(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Translator subagent should write translations for every line via tool calls."""
    context = await load_project_context(tiny_vn_tmp)
    scene_id = "scene_a_00"
    lines = await context.load_scene_lines(scene_id)
    called_threads: list[str] = []

    async def stub_run_with_human_loop(
        agent: object,
        input: object,
        decision_handler: object | None = None,
        thread_id: str | None = None,
    ) -> dict[str, object]:
        _ = agent, input, decision_handler
        called_threads.append(thread_id or "")
        for line in lines:
            translation = TranslatedLine.from_source(
                line, f"translated-{line.id}", text_tgt_origin="agent:stub_translator"
            )
            await context.record_translation(scene_id, translation, allow_overwrite=True)
        return {"done": True}

    monkeypatch.setattr("rentl_agents.subagents.translate_scene.run_with_human_loop", stub_run_with_human_loop)

    result = await translate_scene(context, scene_id, allow_overwrite=True, thread_id="translate-test")

    translations = await context.get_translations(scene_id)
    output_file = tiny_vn_tmp / "output" / "translations" / f"{scene_id}.jsonl"

    assert output_file.exists(), "Expected translations to be written to disk"
    assert result.lines_translated == len(lines)
    assert len(translations) == len(lines)
    assert called_threads, "Expected run_with_human_loop to be invoked with a thread id"
    assert called_threads[0].startswith("translate-test")
    assert all(t.text_tgt.startswith("translated-") for t in translations)


@pytest.mark.anyio
async def test_translation_reviewer_records_checks(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Translation reviewer should record review checks for translated lines."""
    context = await load_project_context(tiny_vn_tmp)
    scene_id = "scene_a_00"
    lines = await context.load_scene_lines(scene_id)
    for line in lines:
        translation = TranslatedLine.from_source(line, f"tgt-{line.id}", text_tgt_origin="agent:prep")
        await context.record_translation(scene_id, translation, allow_overwrite=True)

    class StubReviewer:
        def __init__(self, ctx: ProjectContext) -> None:
            self.ctx = ctx

        async def ainvoke(self, input: object, config: dict | None = None, **_: object) -> dict[str, object]:
            for line in lines:
                await self.ctx.add_translation_check(
                    scene_id, line.id, "translation_review", True, "ok", origin="agent:stub_reviewer"
                )
            return {"done": True}

    def stub_reviewer_factory(context: ProjectContext, *, checkpointer: object | None = None) -> StubReviewer:
        _ = checkpointer
        return StubReviewer(context)

    monkeypatch.setattr(
        "rentl_agents.subagents.translation_reviewer.create_translation_reviewer_subagent", stub_reviewer_factory
    )

    result = await run_translation_review(context, scene_id, thread_id="review-test")

    translations = await context.get_translations(scene_id)
    assert result.checks_recorded == len(lines)
    assert all("translation_review" in t.meta.checks for t in translations)
