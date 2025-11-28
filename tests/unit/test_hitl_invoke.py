"""Unit tests for HITL invocation helper."""
# ruff: noqa: ANN401  # Base Runnable signatures require **kwargs: Any; match exactly for override compatibility.

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.runnables import Runnable, RunnableConfig
from rentl_agents.hitl.invoke import run_with_human_loop


@pytest.fixture
def anyio_backend() -> str:
    """Force asyncio backend for anyio tests.

    Returns:
        str: anyio backend name.
    """
    return "asyncio"


class FakeAgent(Runnable[object, object]):
    """Fake agent that returns predefined responses for ainvoke calls."""

    def __init__(self, responses: Sequence[object]) -> None:
        """Store queued responses and track calls."""
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def invoke(self, input: object, config: RunnableConfig | None = None, **kwargs: Any) -> object:
        """Synchronously invoke by delegating to async implementation for interface completeness."""
        message = "FakeAgent.invoke is not implemented; use ainvoke in tests."
        raise NotImplementedError(message)

    async def ainvoke(self, input: object, config: RunnableConfig | None = None, **kwargs: Any) -> object:
        """Simulate agent invocation by returning queued responses.

        Returns:
            object: Next queued response.

        Raises:
            RuntimeError: If no responses remain.
        """
        self.calls.append({"payload": input, "config": config})
        if not self.responses:
            message = "No more responses queued."
            raise RuntimeError(message)
        return self.responses.pop(0)


@pytest.mark.anyio
async def test_run_with_human_loop_handles_interrupt_and_resume() -> None:
    """Interrupt should call decision handler and resume with provided decisions."""
    interrupt = {"__interrupt__": ["APPROVAL REQUIRED: update translation line_1"]}
    final_result = {"status": "ok"}
    agent = FakeAgent(responses=[interrupt, final_result])

    def decide(requests: list[str]) -> list[str | dict[str, str]]:
        assert "APPROVAL REQUIRED" in requests[0]
        return ["approve"]

    result = await run_with_human_loop(agent, {"messages": []}, decision_handler=decide, thread_id="t-1")

    assert result == final_result
    assert len(agent.calls) == 2
    first_call_config = agent.calls[0]["config"]
    second_call_config = agent.calls[1]["config"]
    assert first_call_config == second_call_config == {"configurable": {"thread_id": "t-1"}}
    assert agent.calls[1]["payload"].resume["decisions"] == [{"type": "approve"}]


@pytest.mark.anyio
async def test_run_with_human_loop_accepts_dict_decisions() -> None:
    """Decision handler may return decision dicts without conversion."""
    interrupt = {"__interrupt__": ["PAUSE"]}
    agent = FakeAgent(responses=[interrupt, {"done": True}])

    def decide(_: list[str]) -> list[str | dict[str, str]]:
        return [{"type": "reject", "message": "skip"}]

    result = await run_with_human_loop(agent, {"messages": []}, decision_handler=decide)
    assert result == {"done": True}
