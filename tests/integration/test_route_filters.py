"""Route-aware filtering tests for pipelines."""

from __future__ import annotations

from pathlib import Path

import pytest
from anyio.lowlevel import checkpoint
from langgraph.checkpoint.memory import MemorySaver
from rentl_agents.subagents.translate_scene import SceneTranslationResult
from rentl_pipelines.flows.context_builder import _run_context_builder_async
from rentl_pipelines.flows.translator import _run_translator_async


@pytest.mark.anyio
async def test_context_builder_filters_by_route(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Context builder should only run scenes belonging to the requested routes."""
    seen: list[str] = []

    async def record_scene(context: object, scene_id: str, **_: object) -> None:
        seen.append(scene_id)
        await checkpoint()

    async def noop(*args: object, **kwargs: object) -> None:
        await checkpoint()

    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene", record_scene)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_character", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_location", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_route", noop)
    from rentl_agents.subagents.glossary_curator import GlossaryDetailResult

    async def glossary_stub(*args: object, **kwargs: object) -> GlossaryDetailResult:
        await checkpoint()
        return GlossaryDetailResult(entries_added=0, entries_updated=0, total_entries=0)

    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_glossary", glossary_stub)

    await _run_context_builder_async(tiny_vn_tmp, route_ids=["route_aya"], concurrency=2, checkpointer=MemorySaver())

    assert seen == ["scene_a_00"], "Only scenes within the selected route should be processed"


@pytest.mark.anyio
async def test_translator_filters_by_route(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Translator should only process scenes for requested routes."""
    translated: list[str] = []

    async def translate_stub(context: object, scene_id: str, **_: object) -> SceneTranslationResult:
        translated.append(scene_id)
        await checkpoint()
        return SceneTranslationResult(scene_id=scene_id, lines_translated=1)

    monkeypatch.setattr("rentl_pipelines.flows.translator.translate_scene", translate_stub)

    result = await _run_translator_async(
        tiny_vn_tmp,
        route_ids=["route_ren"],
        concurrency=2,
        checkpointer=MemorySaver(),
    )

    assert set(translated) == {"scene_r_00", "scene_r_01"}
    assert result.scenes_translated == 2
