"""Helper to run agents with HITL interrupts and resume support."""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import TypeVar, cast
from uuid import uuid4

from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Interrupt
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)

JSONLike = str | int | float | bool | Sequence["JSONLike"] | Mapping[str, "JSONLike"] | None
Decision = dict[str, str] | str
_AgentInput = TypeVar("_AgentInput")
_AgentOutput = TypeVar("_AgentOutput")
InterruptPayload = MutableMapping[str, JSONLike]
# LangGraph interrupt payloads are intentionally loosely typed; confine the weakly typed
# mapping to this module boundary so the rest of the codebase stays strongly typed.


def _extract_interrupt_messages(interrupts: Sequence[Interrupt | JSONLike]) -> list[str]:
    """Normalize interrupt payloads into strings for human review.

    Returns:
        list[str]: Human-readable interrupt messages.
    """
    messages: list[str] = []
    for interrupt in interrupts:
        value = interrupt.value if isinstance(interrupt, Interrupt) else None

        if value is None and isinstance(interrupt, str):
            messages.append(interrupt)
        elif value is None:
            messages.append(str(interrupt))
        elif isinstance(value, str):
            messages.append(value)
        else:
            messages.append(str(value))
    return messages


def _format_decisions(decisions: Sequence[Decision]) -> list[dict[str, str]]:
    """Convert simple string decisions into Command resume payloads.

    Returns:
        list[dict[str, str]]: Normalized decision dicts accepted by Command.
    """
    formatted: list[dict[str, str]] = []
    for decision in decisions:
        if isinstance(decision, dict):
            formatted.append(decision)
        else:
            formatted.append({"type": decision})
    return formatted


async def run_with_human_loop(
    agent: Runnable[_AgentInput | Command, _AgentOutput] | CompiledStateGraph,
    user_input: _AgentInput,
    *,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
) -> _AgentOutput:
    """Invoke an agent and handle HITL interrupts with a decision handler.

    Returns:
        Agent output type: Final agent result after handling any interrupts.

    Raises:
        RuntimeError: If an interrupt occurs and no decision handler was supplied.
    """
    config: RunnableConfig = {"configurable": {"thread_id": thread_id or str(uuid4())}}
    logger.info("Agent invoke start thread_id=%s", config["configurable"]["thread_id"])

    result: _AgentOutput | InterruptPayload = await agent.ainvoke(user_input, config=config)

    while isinstance(result, MutableMapping):
        if "__interrupt__" not in result:
            break

        if decision_handler is None:
            message = "Agent requested approval but no decision handler was provided."
            raise RuntimeError(message)

        interrupt_payload: dict[str, JSONLike] = {str(key): cast(JSONLike, value) for key, value in result.items()}
        interrupt_obj = interrupt_payload.get("__interrupt__")
        if interrupt_obj is None:
            interrupt_seq: Sequence[Interrupt | JSONLike] = []
        elif isinstance(interrupt_obj, Sequence) and not isinstance(interrupt_obj, (str, bytes, bytearray)):
            interrupt_seq = list(interrupt_obj)
        else:
            interrupt_seq = [interrupt_obj]
        requests = _extract_interrupt_messages(interrupt_seq)
        logger.info("Agent interrupt: %s", "; ".join(requests))

        decisions = decision_handler(requests)
        logger.info("Agent decisions: %s", decisions)
        resume_payload = Command(resume={"decisions": _format_decisions(decisions)})
        result = await agent.ainvoke(resume_payload, config=config)

    logger.info("Agent invoke complete thread_id=%s", config["configurable"]["thread_id"])
    return cast(_AgentOutput, result)
