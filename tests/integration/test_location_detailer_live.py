"""Live LLM agentevals-style check for the location detailer subagent."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import cast

import pytest
from agentevals.trajectory.llm import TRAJECTORY_ACCURACY_PROMPT, create_async_trajectory_llm_as_judge
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.subagents.location_detailer import (
    build_location_detailer_user_prompt,
    create_location_detailer_subagent,
)
from rentl_core.context.project import load_project_context
from rentl_core.model.location import LocationMetadata

from tests.helpers.live_llm import run_agent_with_auto_approve


def _extract_tool_call_names(messages: Iterable[BaseMessage]) -> set[str]:
    """Return tool_call names present in a sequence of LC messages."""
    names: set[str] = set()
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            continue
        for call in tool_calls:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            if isinstance(name, str):
                names.add(name)
    return names


@pytest.mark.anyio
@pytest.mark.llm_live
async def test_location_detailer_live_calls_and_language(tiny_vn_tmp: Path, llm_judge_model: str) -> None:
    """Location detailer should call write_* tools and keep description in source language."""
    context = await load_project_context(tiny_vn_tmp)
    location_id = "classroom"

    prompt = build_location_detailer_user_prompt(context, location_id)
    subagent = create_location_detailer_subagent(
        context,
        allow_overwrite=False,
        checkpointer=MemorySaver(),
    )

    result = await run_agent_with_auto_approve(
        subagent,
        {"messages": [{"role": "user", "content": prompt}]},
        thread_id="llm-live:location-detailer:classroom",
    )

    messages = result.get("messages")
    assert isinstance(messages, list), "Expected messages list from location detailer run"
    assert messages, "Expected non-empty messages from location detailer run"
    msg_list = cast(list[BaseMessage], messages)
    tool_names = _extract_tool_call_names(msg_list)
    required_tools = {
        "location_update_name_tgt",
        "location_update_description",
    }
    missing = required_tools - tool_names
    assert not missing, f"Missing expected tool calls: {', '.join(sorted(missing))}"

    updated = context.get_location(location_id)
    assert isinstance(updated, LocationMetadata)
    assert updated.name_tgt, "Expected target name to be recorded"
    assert updated.description, "Expected description to be recorded"

    judge_model = get_default_chat_model()
    judge = create_async_trajectory_llm_as_judge(
        judge=judge_model,
        prompt=TRAJECTORY_ACCURACY_PROMPT,
    )
    eval_result = cast(dict[str, object], await judge(outputs=msg_list))
    if not eval_result.get("score"):
        pytest.fail(f"LLM judge failed location_detailer trajectory: {eval_result}")
