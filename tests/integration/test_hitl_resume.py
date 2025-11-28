"""Integration-style test covering interrupt/resume with run_with_human_loop."""

from __future__ import annotations

import pytest
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.types import Command
from rentl_agents.hitl.invoke import run_with_human_loop


class InterruptingAgent(Runnable[dict[str, object], dict[str, object]]):
    """Minimal agent that interrupts once, then resumes with a final result."""

    def __init__(self) -> None:
        """Track how many times the agent was invoked."""
        self.calls = 0

    def invoke(
        self, input: dict[str, object], config: RunnableConfig | None = None, **kwargs: object
    ) -> dict[str, object]:
        """Synchronous invoke is unused in this test."""
        message = "InterruptingAgent.invoke is not implemented; use ainvoke."
        raise NotImplementedError(message)

    async def ainvoke(
        self, input: dict[str, object], config: RunnableConfig | None = None, **kwargs: object
    ) -> dict[str, object]:
        """Return an interrupt on first call, final result on second."""
        self.calls += 1
        if isinstance(input, Command):
            return {"approvals": ["ok"]}
        if self.calls == 1:
            return {
                "__interrupt__": [
                    {
                        "action_requests": [
                            {
                                "name": "ask",
                                "args": {"message": "need approval"},
                                "description": "Tool execution requires approval",
                            }
                        ]
                    }
                ]
            }
        existing = input.get("approvals")
        approvals = list(existing) if isinstance(existing, list) else []
        return {"approvals": [*approvals, "ok"]}


@pytest.mark.anyio
async def test_hitl_interrupt_and_resume_round_trip() -> None:
    """Ensure an interrupt payload is formatted and resumed end-to-end."""
    intercepted: list[str] = []

    def decide(requests: list[str]) -> list[dict[str, str] | str]:
        intercepted.extend(requests)
        return ["approve"]

    result = await run_with_human_loop(
        InterruptingAgent(),
        {"approvals": []},
        decision_handler=decide,
        thread_id="hitl-resume-test",
    )

    assert intercepted, "Expected interrupt messages"
    assert result["approvals"] == ["ok"]
