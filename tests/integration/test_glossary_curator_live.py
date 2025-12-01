"""Live LLM agentevals-style check for the glossary curator subagent."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import cast

import pytest
from agentevals.trajectory.llm import TRAJECTORY_ACCURACY_PROMPT, create_async_trajectory_llm_as_judge
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.subagents.meta_glossary_curator import (
    build_glossary_curator_user_prompt,
    create_glossary_curator_subagent,
)
from rentl_core.context.project import load_project_context
from rentl_core.model.glossary import GlossaryEntry

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
async def test_glossary_curator_live_calls_and_language(tiny_vn_tmp: Path, llm_judge_model: str) -> None:
    """Glossary curator should call add/update tools and write source/target fields."""
    context = await load_project_context(tiny_vn_tmp)
    prompt = build_glossary_curator_user_prompt(context, current_entries=len(context.glossary))
    subagent = create_glossary_curator_subagent(
        context,
        allow_overwrite=False,
        checkpointer=MemorySaver(),
    )

    result = await run_agent_with_auto_approve(
        subagent,
        {"messages": [{"role": "user", "content": prompt}]},
        thread_id="llm-live:glossary-curator",
    )

    messages = result.get("messages")
    assert isinstance(messages, list), "Expected messages list from glossary curator run"
    assert messages, "Expected non-empty messages from glossary curator run"
    msg_list = cast(list[BaseMessage], messages)
    tool_names = _extract_tool_call_names(msg_list)
    expected_tools = {"glossary_create_entry", "glossary_update_entry"}
    if not (tool_names & expected_tools):
        pytest.fail(f"Expected at least one glossary add/update tool call; seen: {sorted(tool_names)}")

    # Validate glossary entries exist after run
    assert context.glossary, "Expected glossary entries to be present after curation"
    first_entry = context.glossary[0]
    assert isinstance(first_entry, GlossaryEntry)
    assert first_entry.term_src, "Expected source term"
    assert first_entry.term_tgt, "Expected target term"

    judge_model = get_default_chat_model()
    judge = create_async_trajectory_llm_as_judge(
        judge=judge_model,
        prompt=TRAJECTORY_ACCURACY_PROMPT,
    )
    eval_result = cast(dict[str, object], await judge(outputs=flatten_messages(msg_list)))
    if not eval_result.get("score"):
        pytest.fail(f"LLM judge failed glossary_curator trajectory: {eval_result}")
