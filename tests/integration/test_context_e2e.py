"""End-to-end context pipeline test with HITL interrupts and mocked LLMs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from langchain_core.runnables import Runnable
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from rentl_agents.hitl.invoke import run_with_human_loop
from rentl_agents.subagents.meta_glossary_curator import GlossaryDetailResult
from rentl_core.context.project import ProjectContext, load_project_context
from rentl_pipelines.flows.context_builder import ContextBuilderResult, _run_context_builder_async


class InterruptingSceneDetailer:
    """Stub agent that interrupts once, then applies scene metadata on resume."""

    def __init__(self, context: ProjectContext, scene_id: str) -> None:
        """Store context and target scene for later updates."""
        self.context = context
        self.scene_id = scene_id
        self.calls = 0

    async def ainvoke(self, input: object, config: dict | None = None, **_: object) -> dict:
        """Return an interrupt first, then write metadata on resume."""
        if isinstance(input, Command):
            await self.context.set_scene_summary(self.scene_id, f"summary-{self.scene_id}", "agent:test")
            await self.context.set_scene_tags(self.scene_id, ["tag-a", "tag-b"], "agent:test")
            await self.context.set_scene_characters(self.scene_id, ["mc"], "agent:test")
            await self.context.set_scene_locations(self.scene_id, ["classroom"], "agent:test")
            return {"done": True}

        self.calls += 1
        return {"__interrupt__": [{"action_requests": [{"name": "approve", "args": {}, "description": "needed"}]}]}


@pytest.mark.anyio
async def test_context_pipeline_e2e_with_hitl_resume(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Run the full context pipeline with HITL interrupts and mocked agents."""
    project_path = tiny_vn_tmp
    decisions: list[str] = []

    def decision_handler(requests: list[str]) -> list[str | dict[str, str]]:
        decisions.extend(requests)
        return ["approve" for _ in requests]

    async def detail_scene_stub(
        context: ProjectContext,
        scene_id: str,
        *,
        allow_overwrite: bool = False,
        decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
        thread_id: str | None = None,
        checkpointer: MemorySaver | None = None,
    ) -> None:
        """Simulate scene detailing with a single interrupt/resume cycle."""
        _ = (allow_overwrite, checkpointer)
        agent = cast(
            Runnable[dict[str, object] | Command, dict[str, object]],
            InterruptingSceneDetailer(context, scene_id),
        )
        await run_with_human_loop(
            agent,
            {"messages": [{"role": "user", "content": "detail scene"}]},
            decision_handler=decision_handler,
            thread_id=thread_id or f"scene-detail:{scene_id}",
        )

    async def detail_character_stub(context: ProjectContext, character_id: str, **_: object) -> None:
        await context.update_character_name_tgt(character_id, f"{character_id}-tgt", "agent:test")
        await context.update_character_pronouns(character_id, "they/them", "agent:test")
        await context.update_character_notes(character_id, "notes", "agent:test")

    async def detail_location_stub(context: ProjectContext, location_id: str, **_: object) -> None:
        await context.update_location_name_tgt(location_id, f"{location_id}-tgt", "agent:test")
        await context.update_location_description(location_id, "desc", "agent:test")

    async def detail_route_stub(context: ProjectContext, route_id: str, **_: object) -> None:
        await context.update_route_synopsis(route_id, f"synopsis-{route_id}", "agent:test")
        await context.update_route_characters(route_id, ["mc"], "agent:test")

    async def detail_glossary_stub(context: ProjectContext, **_: object) -> GlossaryDetailResult:
        await context.add_glossary_entry("term", "translation", "notes", "agent:test")
        return GlossaryDetailResult(entries_added=1, entries_updated=0, total_entries=1)

    async def detail_scene_tags_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        await context.set_scene_tags(scene_id, ["tag-a"], "agent:test")

    async def detail_scene_characters_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        await context.set_scene_characters(scene_id, ["mc"], "agent:test")

    async def detail_scene_locations_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        await context.set_scene_locations(scene_id, ["classroom"], "agent:test")

    async def detail_scene_glossary_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
        await context.add_glossary_entry("term", "translation", "notes", "agent:test")

    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene_summary", detail_scene_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene_tags", detail_scene_tags_stub)
    monkeypatch.setattr(
        "rentl_pipelines.flows.context_builder.detail_scene_primary_characters", detail_scene_characters_stub
    )
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene_locations", detail_scene_locations_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene_glossary", detail_scene_glossary_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.curate_character", detail_character_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.curate_location", detail_location_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.build_route_outline", detail_route_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_glossary", detail_glossary_stub)

    result: ContextBuilderResult = await _run_context_builder_async(
        project_path,
        concurrency=2,
        checkpointer=MemorySaver(),
        decision_handler=decision_handler,
    )

    context = await load_project_context(project_path)
    for scene in context.scenes.values():
        ann = scene.annotations
        assert ann.summary, "Expected scene summary to be set"
        assert ann.tags, "Expected scene tags to be set"
        assert ann.primary_characters, "Expected primary characters to be set"
        assert ann.locations, "Expected locations to be set"

    for character in context.characters.values():
        assert character.name_tgt, "Expected character target name"
        assert character.pronouns, "Expected character pronouns"
        assert character.notes, "Expected character notes"

    for location in context.locations.values():
        assert location.name_tgt, "Expected location target name"
        assert location.description, "Expected location description"

    for route in context.routes.values():
        assert route.synopsis, "Expected route synopsis"
        assert route.primary_characters, "Expected route primary characters"

    assert decisions, "Expected HITL decision handler to be invoked"
    assert result.scenes_detailed == len(context.scenes)
    assert not result.errors
    assert result.scenes_skipped == 0
