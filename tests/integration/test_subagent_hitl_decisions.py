"""Integration test to ensure subagent HITL decisions flow through run_with_human_loop."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from rentl_agents.subagents.scene_summary_detailer import detail_scene_summary
from rentl_core.context.project import ProjectContext, load_project_context


class InterruptingDetailer:
    """Stub subagent that interrupts once and applies updates on resume."""

    def __init__(self, context: ProjectContext) -> None:
        """Store context for later updates."""
        self.context = context
        self.calls = 0

    async def ainvoke(self, input: object, config: dict | None = None, **_: object) -> dict:
        """Return an interrupt first, then apply updates when resumed."""
        thread_id = ""
        if config and isinstance(config, dict):
            thread_id = str(config.get("configurable", {}).get("thread_id", ""))
        if isinstance(input, Command):
            scene_id = thread_id.split(":")[-1]
            await self.context.set_scene_summary(scene_id, "SOURCE SUMMARY", "agent:test")
            return {"done": True}
        self.calls += 1
        return {
            "__interrupt__": [{"action_requests": [{"name": "approve", "args": {}, "description": "need approval"}]}]
        }


@pytest.mark.anyio
async def test_scene_summary_detailer_hitl_flow(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Scene summary detailer should request approval and apply updates after approval."""
    context = await load_project_context(tiny_vn_tmp)
    decisions: list[str] = []

    def decision_handler(requests: list[str]) -> list[str | dict[str, str]]:
        decisions.extend(requests)
        return ["approve"]

    def stub_creator(
        context: ProjectContext, *, allow_overwrite: bool, checkpointer: MemorySaver
    ) -> InterruptingDetailer:  # type: ignore[override]
        _ = (allow_overwrite, checkpointer)
        return InterruptingDetailer(context)

    monkeypatch.setattr(
        "rentl_agents.subagents.scene_summary_detailer.create_scene_summary_detailer_subagent", stub_creator
    )

    result = await detail_scene_summary(
        context,
        "scene_a_00",
        allow_overwrite=False,
        decision_handler=decision_handler,
        thread_id="hitl-scene-test",
        checkpointer=MemorySaver(),
    )

    assert decisions, "Expected HITL decision requests to be surfaced"
    assert result.summary == "SOURCE SUMMARY"
    assert result.summary == "SOURCE SUMMARY"


@pytest.mark.anyio
async def test_scene_summary_detailer_reject_keeps_existing(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Reject decisions should result in no metadata updates."""
    context = await load_project_context(tiny_vn_tmp)
    decisions: list[str] = []

    class RejectingDetailer(InterruptingDetailer):
        async def ainvoke(self, input: object, config: dict | None = None, **_: object) -> dict:
            if isinstance(input, Command):
                return {"done": False}
            return {"__interrupt__": [{"action_requests": [{"name": "approve", "args": {}, "description": "need"}]}]}

    def reject_creator(
        context: ProjectContext, *, allow_overwrite: bool, checkpointer: MemorySaver
    ) -> RejectingDetailer:  # type: ignore[override]
        _ = (allow_overwrite, checkpointer)
        return RejectingDetailer(context)

    def decision_handler(requests: list[str]) -> list[str | dict[str, str]]:
        decisions.extend(requests)
        return ["reject"]

    monkeypatch.setattr(
        "rentl_agents.subagents.scene_summary_detailer.create_scene_summary_detailer_subagent", reject_creator
    )

    await detail_scene_summary(
        context,
        "scene_a_00",
        allow_overwrite=False,
        decision_handler=decision_handler,
        thread_id="hitl-scene-reject",
        checkpointer=MemorySaver(),
    )

    scene = context.get_scene("scene_a_00")
    assert not scene.annotations.summary
    assert not scene.annotations.summary
    assert decisions, "Expected a decision request to be surfaced"
