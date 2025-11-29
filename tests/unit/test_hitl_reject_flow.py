"""Ensure run_with_human_loop propagates reject decisions."""

from __future__ import annotations

from typing import cast

import anyio
import pytest
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.types import Command
from rentl_agents.hitl.invoke import run_with_human_loop


class RejectingAgent(Runnable[dict[str, object] | Command, dict[str, object]]):
    """Minimal agent that interrupts and expects a reject decision."""

    def __init__(self) -> None:
        """Initialize decision storage."""
        super().__init__()
        self.seen_decisions: list[dict[str, str]] = []

    async def ainvoke(
        self, input: dict[str, object] | Command, config: RunnableConfig | None = None, **_: object
    ) -> dict[str, object]:
        """Interrupt first; on resume capture decisions and mark rejected.

        Returns:
            dict[str, object]: Interrupt payload or final status.
        """
        if isinstance(input, Command):
            resume_payload: dict[str, object] = (
                cast(dict[str, object], input.resume) if isinstance(input.resume, dict) else {}
            )
            decisions_raw = resume_payload.get("decisions", [])
            if isinstance(decisions_raw, list):
                for decision in decisions_raw:
                    if isinstance(decision, dict):
                        typed_decision = {str(k): str(v) for k, v in decision.items()}
                        self.seen_decisions.append(typed_decision)
            return {"status": "rejected"}
        return {"__interrupt__": [{"action_requests": [{"name": "approve", "args": {}, "description": "need"}]}]}

    def invoke(
        self, input: dict[str, object] | Command, config: RunnableConfig | None = None, **kwargs: object
    ) -> dict[str, object]:
        """Synchronous invoke delegates to the async implementation for compatibility.

        Returns:
            dict[str, object]: Final status or interrupt payload.
        """
        _ = kwargs
        return anyio.run(self.ainvoke, input, config)


@pytest.mark.anyio
async def test_run_with_human_loop_reject_decision() -> None:
    """Reject decisions should be passed back to the agent."""
    agent = RejectingAgent()

    def decide(requests: list[str]) -> list[dict[str, str] | str]:
        assert requests, "Expected interrupt requests"
        return ["reject"]

    result = await run_with_human_loop(agent, {"input": "x"}, decision_handler=decide, thread_id="reject-test")

    assert result["status"] == "rejected"
    assert agent.seen_decisions == [{"type": "reject"}]
