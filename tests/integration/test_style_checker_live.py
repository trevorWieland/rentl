"""Live LLM agentevals-style check for the style checker subagent."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import cast

import pytest
from agentevals.trajectory.llm import TRAJECTORY_ACCURACY_PROMPT, create_async_trajectory_llm_as_judge
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.subagents.style_checks import build_style_checker_user_prompt, create_style_checker_subagent
from rentl_core.context.project import load_project_context

from tests.helpers.live_llm import flatten_messages, run_agent_with_auto_approve


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
async def test_style_checker_live_calls_and_language(tiny_vn_tmp: Path, llm_judge_model: str) -> None:
    """Style checker should read translations and record style checks."""
    context = await load_project_context(tiny_vn_tmp)
    scene_id = "scene_a_00"

    prompt = build_style_checker_user_prompt(scene_id)
    subagent = create_style_checker_subagent(
        context,
        checkpointer=MemorySaver(),
    )

    result = await run_agent_with_auto_approve(
        subagent,
        {"messages": [{"role": "user", "content": prompt}]},
        thread_id="llm-live:style-checker:scene_a_00",
    )

    messages = result.get("messages")
    assert isinstance(messages, list), "Expected messages list from style checker run"
    assert messages, "Expected non-empty messages from style checker run"
    msg_list = cast(list[BaseMessage], messages)
    tool_names = _extract_tool_call_names(msg_list)
    required_tools = {"read_translations", "record_style_check"}
    missing = required_tools - tool_names
    assert not missing, f"Missing expected tool calls: {', '.join(sorted(missing))}"

    translations = await context.get_translations(scene_id)
    assert translations, "Expected translations to exist for style checks"
    assert any("style_check" in t.meta.checks for t in translations), "Expected style checks recorded"

    judge_model = get_default_chat_model()
    judge = create_async_trajectory_llm_as_judge(
        judge=judge_model,
        prompt=TRAJECTORY_ACCURACY_PROMPT,
    )
    eval_result = cast(dict[str, object], await judge(outputs=flatten_messages(msg_list)))
    if not eval_result.get("score"):
        reason = eval_result.get("comment") or eval_result
        pytest.fail(f"LLM judge failed style_checker trajectory: {reason}")
