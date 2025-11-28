"""Tests for hitl.invoke formatting and decision handling."""

from __future__ import annotations

from rentl_agents.hitl.invoke import _extract_interrupt_messages, _format_decisions


def test_extract_interrupt_messages_action_requests() -> None:
    """Action requests should render minimal tool/args/reason strings."""
    messages = _extract_interrupt_messages(
        [
            {
                "value": {
                    "__interrupt__": "unused",
                    "action_requests": [
                        {
                            "name": "write_scene_summary",
                            "args": {"scene_id": "s1"},
                            "description": "overwrite human data",
                        },
                    ],
                }
            }
        ]
    )
    assert messages == ["write_scene_summary args={'scene_id': 's1'} reason=overwrite human data"]


def test_extract_interrupt_messages_strings() -> None:
    """Plain strings should passthrough."""
    messages = _extract_interrupt_messages(["simple message"])
    assert messages == ["simple message"]


def test_format_decisions_strings_and_dicts() -> None:
    """Decision formatting should normalize strings and dict decisions."""
    decisions = _format_decisions(["approve", {"type": "reject", "message": "skip"}])
    assert decisions == [{"type": "approve"}, {"type": "reject", "message": "skip"}]
