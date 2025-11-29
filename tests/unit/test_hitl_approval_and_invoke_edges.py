"""Edge coverage for HITL approval helpers and interrupt parsing."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.types import Command, Interrupt
from rentl_agents.hitl.approval import (
    ApprovalGate,
    ApprovalPolicy,
    check_entry_approval,
    check_field_approval,
    format_approval_request,
    is_agent_authored,
    is_human_authored,
)
from rentl_agents.hitl.invoke import _extract_interrupt_messages, run_with_human_loop


def test_is_human_agent_authored() -> None:
    """Basic provenance helpers should distinguish human/agent."""
    assert is_human_authored("human")
    assert not is_human_authored(None)
    assert not is_human_authored("agent:foo")
    assert is_agent_authored("agent:scene_detailer:2024-01-01")
    assert not is_agent_authored("human")
    assert not is_agent_authored(None)


def test_check_field_approval_policies() -> None:
    """Check field approval across policies and provenance."""
    assert not check_field_approval(None, None, ApprovalPolicy.STANDARD)
    assert check_field_approval("value", "human", ApprovalPolicy.STANDARD)
    assert not check_field_approval("value", "agent:x", ApprovalPolicy.STANDARD)
    assert not check_field_approval("value", "human", ApprovalPolicy.PERMISSIVE)
    assert check_field_approval("value", None, ApprovalPolicy.STRICT)


def test_check_entry_approval_multiple_fields() -> None:
    """Check entry approval when any origin is human-authored."""
    entry: Mapping[str, str | None] = {
        "a_origin": "human",
        "b_origin": "agent:x",
    }
    assert check_entry_approval(entry, ["a_origin", "b_origin"], ApprovalPolicy.STANDARD)
    assert not check_entry_approval(entry, ["b_origin"], ApprovalPolicy.STANDARD)
    assert check_entry_approval(entry, ["b_origin"], ApprovalPolicy.STRICT)
    assert not check_entry_approval(entry, ["a_origin"], ApprovalPolicy.PERMISSIVE)


def test_format_approval_request_includes_reason_and_values() -> None:
    """Approval request string should include reason and value diffs."""
    msg = format_approval_request("update", "character.aya.name_tgt", "human-authored", "Aya", "Aya B.")
    assert "APPROVAL REQUIRED" in msg
    assert "human-authored" in msg
    assert "Aya" in msg
    assert "Aya B." in msg


def test_approval_gate_basic() -> None:
    """ApprovalGate should require approval for human-authored fields."""
    gate = ApprovalGate(policy=ApprovalPolicy.STANDARD, operation="update", target="char.aya.name")
    assert gate.requires_approval("Aya", "human")
    req = gate.format_request("human-authored", "Aya", "Aya B.")
    assert "APPROVAL REQUIRED" in req
    assert "Aya B." in req


@pytest.mark.anyio
async def test_run_with_human_loop_handles_malformed_interrupt() -> None:
    """Malformed interrupt payloads should be stringified without errors."""
    intercepted: list[str] = []

    class BadInterruptAgent(Runnable[dict[str, object] | Command, dict[str, object]]):
        def invoke(
            self,
            input: dict[str, object] | Command,
            config: RunnableConfig | None = None,
            **_: object,
        ) -> dict[str, object]:
            raise NotImplementedError

        async def ainvoke(
            self,
            input: dict[str, object] | Command,
            config: RunnableConfig | None = None,
            **_: object,
        ) -> dict[str, object]:
            if isinstance(input, Command):
                return {"ok": True}
            return {
                "__interrupt__": [
                    "plain string",
                    Interrupt(value={"unexpected": "payload"}),
                    {"value": {"other": "data"}},
                ]
            }

    def decide(requests: list[str]) -> list[dict[str, str] | str]:
        intercepted.extend(requests)
        return ["approve"]

    result = await run_with_human_loop(
        BadInterruptAgent(),
        {"messages": [{"role": "user", "content": "start"}]},
        decision_handler=decide,
        thread_id="hitl-malformed",
    )
    assert result == {"ok": True}
    # All interrupt variants should have been converted to strings
    assert intercepted
    assert all(isinstance(msg, str) for msg in intercepted)


def test_extract_interrupt_messages_various_shapes() -> None:
    """Ensure _extract_interrupt_messages handles multiple payload shapes."""
    messages = _extract_interrupt_messages(
        [
            Interrupt(value={"action_requests": [{"name": "approve", "args": {}, "description": "need it"}]}),
            {"action_requests": [{"name": "edit", "args": {"value": 1}, "description": ""}]},
            {"value": {"action_requests": [{"name": "reject", "args": {}, "description": "nope"}]}},
            "string interrupt",
            123,
        ]
    )
    assert "approve" in messages[0]
    assert "edit" in messages[1]
    assert "reject" in messages[2]
    assert "string interrupt" in messages[3]
    assert "123" in messages[4]
