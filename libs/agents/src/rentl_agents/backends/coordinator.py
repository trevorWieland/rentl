"""Coordinator agent factory without filesystem tools."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.subagents import CompiledSubAgent, SubAgent, SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, InterruptOnConfig, TodoListMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain.agents.structured_output import ResponseFormat
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

BASE_AGENT_PROMPT = (
    "In order to complete the objective that the user asks of you, you have access to subagents and progress tools. "
    "Do not use filesystem or execution tools."
)


def create_coordinator_agent(
    model: str | BaseChatModel,
    tools: Sequence[BaseTool | Any] | None = None,
    *,
    system_prompt: str | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    response_format: ResponseFormat | None = None,
    checkpointer: Checkpointer | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    name: str | None = None,
) -> CompiledStateGraph:
    """Create a coordinator agent without filesystem middleware.

    Returns:
        CompiledStateGraph: LangGraph graph configured for coordination.
    """
    base_middleware: list[AgentMiddleware] = [
        TodoListMiddleware(),
        SubAgentMiddleware(
            default_model=model,
            default_tools=tools,
            subagents=subagents if subagents is not None else [],
            default_middleware=[TodoListMiddleware(), PatchToolCallsMiddleware()],
            default_interrupt_on=interrupt_on,
            general_purpose_agent=False,
        ),
        PatchToolCallsMiddleware(),
    ]
    if middleware:
        base_middleware.extend(middleware)
    if interrupt_on is not None:
        base_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    prompt = system_prompt + "\n\n" + BASE_AGENT_PROMPT if system_prompt else BASE_AGENT_PROMPT

    return create_agent(
        model=model,
        tools=tools or [],
        system_prompt=prompt,
        middleware=base_middleware,
        response_format=response_format,
        checkpointer=checkpointer,
        name=name,
    )
