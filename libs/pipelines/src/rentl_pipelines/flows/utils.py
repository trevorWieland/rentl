"""Shared helpers for pipeline execution."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol, cast
from uuid import uuid4

from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


class SupportsAinvoke(Protocol):
    """Protocol for DeepAgent-like objects that expose ``ainvoke``."""

    async def ainvoke(self, input: object, *, config: dict | None = None) -> object:
        """Invoke the agent asynchronously."""


def _extract_interrupt_messages(interrupts: Sequence[object]) -> list[str]:
    """Normalize interrupt payloads into printable strings.

    Args:
        interrupts: Sequence of interrupt payloads from the agent.

    Returns:
        List of stringified interrupt messages.
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


async def invoke_with_interrupts(
    agent: SupportsAinvoke,
    user_input: object,
    *,
    decision_handler: Callable[[list[str]], list[str]] | None = None,
    thread_id: str | None = None,
) -> object:
    """Invoke a DeepAgent and handle HITL interrupts by delegating to a decision handler.

    Args:
        agent: DeepAgent instance exposing ``ainvoke``.
        user_input: Input payload for ``ainvoke`` (message dict or Command).
        decision_handler: Callable that accepts interrupt messages and returns decisions.
        thread_id: Optional thread id for the agent checkpointer.

    Raises:
        RuntimeError: If the agent requests approval and no decision handler is provided.

    Returns:
        Final agent result after handling interrupts.
    """
    config = {"configurable": {"thread_id": thread_id or str(uuid4())}}
    logger.info("Agent invoke start thread_id=%s", config["configurable"]["thread_id"])
    result = await agent.ainvoke(user_input, config=config)

    no_handler_error = "Agent requested approval but no decision handler was provided."
    while isinstance(result, dict) and "__interrupt__" in result:
        if decision_handler is None:
            raise RuntimeError(no_handler_error)

        typed_result = cast(dict[str, object], result)
        interrupt_obj = typed_result.get("__interrupt__")
        interrupt_seq: Sequence[object] = interrupt_obj if isinstance(interrupt_obj, Sequence) else [interrupt_obj]
        requests = _extract_interrupt_messages(interrupt_seq)
        logger.info("Agent interrupt: %s", "; ".join(requests))
        decisions = decision_handler(requests)
        logger.info("Agent decisions: %s", decisions)
        resume_payload = {"resume": {"decisions": decisions}}
        result = await agent.ainvoke(resume_payload, config=config)

    logger.info("Agent invoke complete thread_id=%s", config["configurable"]["thread_id"])
    return result
