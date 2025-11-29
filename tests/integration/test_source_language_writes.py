"""Ensure context detailers record source-language metadata."""

from __future__ import annotations

from pathlib import Path

import pytest
from anyio.lowlevel import checkpoint
from langgraph.checkpoint.memory import MemorySaver
from rentl_agents.subagents.glossary_curator import GlossaryDetailResult
from rentl_core.context.project import ProjectContext, load_project_context
from rentl_pipelines.flows.context_builder import _run_context_builder_async


@pytest.mark.anyio
async def test_context_builder_preserves_source_language(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Stub detailers write source-language metadata and it should persist unchanged."""
    source_summary = "Un resumen en español"
    source_tags = ["tag_es", "inicio"]
    source_locations = ["escuela"]

    async def scene_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        await context.set_scene_summary(scene_id, source_summary, "agent:test")
        await context.set_scene_tags(scene_id, source_tags, "agent:test")
        await context.set_scene_characters(scene_id, ["mc"], "agent:test")
        await context.set_scene_locations(scene_id, source_locations, "agent:test")

    async def noop(*args: object, **kwargs: object) -> None:
        await checkpoint()

    async def glossary_stub(*args: object, **kwargs: object) -> GlossaryDetailResult:
        await checkpoint()
        return GlossaryDetailResult(entries_added=0, entries_updated=0, total_entries=0)

    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene", scene_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_character", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_location", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_route", noop)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_glossary", glossary_stub)

    await _run_context_builder_async(
        tiny_vn_tmp,
        scene_ids=["scene_a_00"],
        concurrency=1,
        checkpointer=MemorySaver(),
    )

    context = await load_project_context(tiny_vn_tmp)
    scene = context.get_scene("scene_a_00")
    assert scene.annotations.summary == source_summary
    assert scene.annotations.tags == source_tags
    assert scene.annotations.locations == source_locations
