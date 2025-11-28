"""Shared HITL helper functions for tool implementations."""

from __future__ import annotations

from rentl_agents.hitl.approval import ApprovalGate, ApprovalPolicy


def request_if_human_authored(
    *,
    operation: str,
    target: str,
    current_value: object,
    current_origin: str | None,
    proposed_value: object,
    policy: ApprovalPolicy = ApprovalPolicy.STANDARD,
) -> str | None:
    """Return an approval request message when overwriting human-authored data."""
    if current_value == proposed_value:
        return "No change: proposed value matches current value."

    gate = ApprovalGate(policy=policy, operation=operation, target=target)
    if gate.requires_approval(current_value, current_origin):
        return gate.format_request(
            reason="human-authored field",
            old_value=current_value,
            new_value=proposed_value,
        )
    return None
