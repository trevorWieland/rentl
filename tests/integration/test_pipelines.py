"""Integration-style tests for pipeline orchestration with real ProjectContext."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from langgraph.checkpoint.memory import MemorySaver
from rentl_agents.subagents.consistency_checks import ConsistencyCheckResult
from rentl_agents.subagents.glossary_curator import GlossaryDetailResult
from rentl_agents.subagents.style_checks import StyleCheckResult
from rentl_agents.subagents.translate_scene import SceneTranslationResult
from rentl_agents.subagents.translation_reviewer import TranslationReviewResult
from rentl_pipelines.flows.context_builder import ContextBuilderResult, _run_context_builder_async
from rentl_pipelines.flows.editor import EditorResult, _run_editor_async
from rentl_pipelines.flows.translator import TranslatorResult, _run_translator_async


@pytest.mark.anyio
async def test_context_builder_retries_and_records_progress(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Context Builder should retry transient failures and report completions."""
    project_path = tiny_vn_tmp

    attempts: dict[str, int] = {"scene_detail": 0}

    async def flaky_scene_detail(*args: object, **kwargs: object) -> None:
        attempts["scene_detail"] += 1
        if attempts["scene_detail"] == 1:
            raise RuntimeError
        await anyio.sleep(0.001)

    async def noop(*args: object, **kwargs: object) -> None:  # context/ids supplied by pipeline
        await anyio.sleep(0.001)

    async def noop_glossary(*args: object, **kwargs: object) -> GlossaryDetailResult:
        await anyio.sleep(0.001)
        return GlossaryDetailResult(entries_added=0, entries_updated=0, total_entries=0)

    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene", flaky_scene_detail)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_character", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_location", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_route", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_glossary", noop_glossary)

    progress_events: list[tuple[str, str]] = []

    def progress_cb(event: str, entity: str) -> None:
        progress_events.append((event, entity))

    result: ContextBuilderResult = await _run_context_builder_async(
        project_path,
        concurrency=2,
        progress_cb=progress_cb,
        checkpointer=MemorySaver(),
    )

    # All entities should complete despite one transient failure.
    assert result.scenes_detailed == 4
    assert result.characters_detailed == 3
    assert result.locations_detailed == 2
    assert result.routes_detailed == 3
    assert result.errors == []
    # Progress callback should have at least one start/done event.
    assert any(evt[0].endswith("_start") for evt in progress_events)
    assert any(evt[0].endswith("_done") for evt in progress_events)


@pytest.mark.anyio
async def test_translator_records_errors_without_stopping(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Translator should continue other scenes and capture errors."""
    project_path = tiny_vn_tmp

    async def translate_or_fail(context: object, scene_id: str, **kwargs: object) -> SceneTranslationResult:
        if scene_id.endswith("01"):
            raise ValueError
        await anyio.sleep(0.001)
        return SceneTranslationResult(scene_id=scene_id, lines_translated=1)

    monkeypatch.setattr("rentl_pipelines.flows.translator.translate_scene", translate_or_fail)

    result: TranslatorResult = await _run_translator_async(
        project_path,
        concurrency=2,
        checkpointer=MemorySaver(),
    )

    assert result.errors, "Expected errors to be captured for failing scenes."
    failed_ids = {err.entity_id for err in result.errors}
    assert "scene_r_01" in failed_ids
    # Remaining scenes should be counted as translated.
    assert result.scenes_translated == 3
    assert result.scenes_skipped == 0


@pytest.mark.anyio
async def test_editor_records_errors_without_stopping(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Editor should continue other scenes and capture errors."""
    project_path = tiny_vn_tmp

    async def style_ok(context: object, scene_id: str, **kwargs: object) -> StyleCheckResult:
        await anyio.sleep(0.001)
        return StyleCheckResult(scene_id=scene_id, checks_recorded=1)

    async def consistency_ok(context: object, scene_id: str, **kwargs: object) -> ConsistencyCheckResult:
        await anyio.sleep(0.001)
        return ConsistencyCheckResult(scene_id=scene_id, checks_recorded=1)

    async def review_or_fail(context: object, scene_id: str, **kwargs: object) -> TranslationReviewResult:
        if scene_id.endswith("01"):
            raise RuntimeError
        await anyio.sleep(0.001)
        return TranslationReviewResult(scene_id=scene_id, checks_recorded=1)

    monkeypatch.setattr("rentl_pipelines.flows.editor.run_style_checks", style_ok)
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_consistency_checks", consistency_ok)
    monkeypatch.setattr("rentl_pipelines.flows.editor.run_translation_review", review_or_fail)

    result: EditorResult = await _run_editor_async(
        project_path,
        concurrency=2,
        checkpointer=MemorySaver(),
    )

    assert result.errors, "Expected errors to be captured for failing scenes."
    failed_ids = {err.entity_id for err in result.errors}
    assert "scene_r_01" in failed_ids
    # Scenes counted as checked even if later QA stage fails for one scene.
    assert result.scenes_checked == 4
    assert result.translation_progress >= 0.0
    assert result.editing_progress >= 0.0
    assert isinstance(result.route_issue_counts, dict)
