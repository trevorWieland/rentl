"""Helper to run agents with HITL interrupts and resume support."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast
from uuid import uuid4

from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


def _extract_interrupt_messages(interrupts: Sequence[object]) -> list[str]:
    """Normalize interrupt payloads into strings for human review.

    Returns:
        list[str]: Human-readable interrupt messages.
    """
    messages: list[str] = []
    for interrupt in interrupts:
        value = getattr(interrupt, "value", None)
        if value is None:
            messages.append(str(interrupt))
        elif isinstance(value, str):
            messages.append(value)
        else:
            messages.append(str(value))
    return messages


def _format_decisions(decisions: list[str | dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert simple string decisions into Command resume payloads.

    Returns:
        list[dict[str, Any]]: Normalized decision dicts accepted by Command.
    """
    formatted: list[dict[str, Any]] = []
    for decision in decisions:
        if isinstance(decision, dict):
            formatted.append(decision)
        else:
            formatted.append({"type": decision})
    return formatted


async def run_with_human_loop(
    agent: Runnable | CompiledStateGraph,
    user_input: object,
    *,
    decision_handler: Callable[[list[str]], list[str | dict[str, Any]]] | None = None,
    thread_id: str | None = None,
) -> object:
    """Invoke an agent and handle HITL interrupts with a decision handler.

    Returns:
        object: Final agent result after handling any interrupts.

    Raises:
        RuntimeError: If an interrupt occurs and no decision handler was supplied.
    """
    config: RunnableConfig = {"configurable": {"thread_id": thread_id or str(uuid4())}}
    logger.info("Agent invoke start thread_id=%s", config["configurable"]["thread_id"])

    result = await agent.ainvoke(user_input, config=config)

    while isinstance(result, dict) and "__interrupt__" in result:
        if decision_handler is None:
            message = "Agent requested approval but no decision handler was provided."
            raise RuntimeError(message)

        typed_result: dict[str, object] = cast(dict[str, object], result)
        interrupt_obj = typed_result.get("__interrupt__")
        interrupt_seq: Sequence[object] = interrupt_obj if isinstance(interrupt_obj, Sequence) else [interrupt_obj]
        requests = _extract_interrupt_messages(interrupt_seq)
        logger.info("Agent interrupt: %s", "; ".join(requests))

        decisions = decision_handler(requests)
        logger.info("Agent decisions: %s", decisions)
        resume_payload = Command(resume={"decisions": _format_decisions(decisions)})
        result = await agent.ainvoke(resume_payload, config=config)

    logger.info("Agent invoke complete thread_id=%s", config["configurable"]["thread_id"])
    return result
