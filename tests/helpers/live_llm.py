"""Helpers for running live LLM subagent tests without mocks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from rentl_agents.hitl.invoke import Decision, run_with_human_loop


async def run_agent_with_auto_approve(
    agent: CompiledStateGraph | Runnable[dict[str, object] | Command, dict[str, object]],
    user_input: dict[str, object],
    *,
    thread_id: str | None = None,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
) -> dict[str, object]:
    """Run an agent with a default approve-all HITL handler and return the raw result.

    Args:
        agent: A LangChain agent runnable/graph (e.g., create_agent output).
        user_input: Input payload to send (usually {"messages": [...]})
        thread_id: Optional thread id for resumable runs.
        decision_handler: Optional override to handle action requests; defaults to approve-all.

    Returns:
        dict[str, object]: Agent output (raw), typically containing "messages" for trajectory checks.
    """

    def _default_decider(requests: list[str]) -> list[Decision]:
        return [{"type": "approve"} for _ in requests] or [{"type": "approve"}]

    handler = decision_handler or _default_decider
    result = await run_with_human_loop(
        agent,
        user_input,
        decision_handler=handler,
        thread_id=thread_id,
    )
    if isinstance(result, dict):
        return result
    return {"result": result}


def flatten_messages(messages: list[Any]) -> list[dict[str, str]]:
    """Convert LangChain messages to simple role/content dicts for LLM judging.

    Returns:
        list[dict[str, str]]: Flattened messages with role and content only.
    """
    flat: list[dict[str, str]] = []
    for msg in messages:
        role = getattr(msg, "type", msg.__class__.__name__)
        content_val = getattr(msg, "content", "")
        content = content_val if isinstance(content_val, str) else str(content_val)
        flat.append({"role": str(role), "content": content})
    return flat
