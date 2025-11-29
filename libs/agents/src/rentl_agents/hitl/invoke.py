"""Helper to run agents with HITL interrupts and resume support."""

from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import NotRequired, TypeVar, cast
from uuid import uuid4

from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Interrupt
from rentl_core.util.logging import get_logger
from typing_extensions import TypedDict

logger = get_logger(__name__)

JSONLike = str | int | float | bool | Sequence["JSONLike"] | Mapping[str, "JSONLike"] | None
Decision = dict[str, str] | str
_AgentInput = TypeVar("_AgentInput")
_AgentOutput = TypeVar("_AgentOutput")
InterruptPayload = MutableMapping[str, JSONLike]
# LangGraph interrupt payloads are intentionally loosely typed; confine the weakly typed
# mapping to this module boundary so the rest of the codebase stays strongly typed.


class ActionRequest(TypedDict):
    """Shape emitted by LangGraph HITL middleware."""

    name: str
    args: Mapping[str, object]
    description: NotRequired[str]


def _extract_interrupt_messages(interrupts: Sequence[Interrupt | JSONLike]) -> list[str]:
    """Normalize interrupt payloads into strings for human review.

    Returns:
        list[str]: Human-readable interrupt messages.
    """
    messages: list[str] = []
    for interrupt in interrupts:
        value = interrupt.value if isinstance(interrupt, Interrupt) else None
        payload: Mapping[str, object] | None = None
        if isinstance(value, Mapping):
            payload = value
        elif isinstance(interrupt, Mapping) and not isinstance(interrupt, (str, bytes, bytearray)):
            payload = cast(Mapping[str, object], interrupt)

        if payload and "value" in payload:
            nested_value = payload.get("value")
            if isinstance(nested_value, Mapping):
                payload = cast(Mapping[str, object], nested_value)

        if isinstance(payload, Mapping) and "action_requests" in payload:
            requests = payload.get("action_requests")
            if isinstance(requests, Sequence):
                parsed_any = False
                for req in requests:
                    if isinstance(req, Mapping):
                        req_map = cast(Mapping[str, object], req)
                        name_val = req_map.get("name", None)
                        name = name_val if isinstance(name_val, str) else "<unknown>"
                        args = req_map.get("args", {})
                        desc = req_map.get("description", "")
                        reason = desc.splitlines()[0] if isinstance(desc, str) and desc else ""
                        messages.append(f"{name} args={args} reason={reason}")
                        parsed_any = True
                    else:
                        messages.append(str(req))
                if parsed_any:
                    continue

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
