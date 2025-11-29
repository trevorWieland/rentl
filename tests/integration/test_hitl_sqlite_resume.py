"""Integration test covering HITL interrupt/resume with a SQLite checkpointer."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field


class ApprovalState(BaseModel):
    """Graph state for the interrupt/resume smoke test."""

    steps: list[str] = Field(default_factory=list)


@pytest.mark.anyio
async def test_interrupt_resume_round_trip_with_sqlite(tmp_path: Path) -> None:
    """Interrupt/resume should persist state through a SQLite-backed checkpointer."""
    db_path = tmp_path / ".rentl" / "checkpoints.db"
    await anyio.Path(db_path.parent).mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:

        def request_approval(state: ApprovalState) -> ApprovalState:
            """Interrupt to ask for approval, then record the provided decision.

            Returns:
                ApprovalState: Updated state with the new decision appended.
            """
            answer = interrupt("need approval")
            steps = list(state.steps)
            return ApprovalState(steps=[*steps, answer])

        builder = StateGraph(ApprovalState)
        builder.add_node("request_approval", request_approval)
        builder.add_edge(START, "request_approval")
        builder.add_edge("request_approval", END)
        agent = builder.compile(checkpointer=checkpointer)

        config: RunnableConfig = {"configurable": {"thread_id": "interrupt-sqlite-test"}}
        initial_chunks = [chunk async for chunk in agent.astream(ApprovalState(), config=config)]
        assert initial_chunks, "Expected an interrupt chunk"
        assert "__interrupt__" in initial_chunks[-1]

        resumed_chunks = [chunk async for chunk in agent.astream(Command(resume="approved"), config=config)]
        final_state = resumed_chunks[-1].get("request_approval") if resumed_chunks else None
        if isinstance(final_state, ApprovalState):
            final_state = final_state.model_dump()
        assert final_state == {"steps": ["approved"]}

    assert db_path.exists(), "SQLite checkpoint file should be created"
