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
    """Return an approval request message when overwriting human-authored data.

    Args:
        operation: Operation name (e.g., "update").
        target: Target identifier (e.g., "scene.scene_a_00.summary").
        current_value: Current field value.
        current_origin: Current field provenance (``*_origin``).
        proposed_value: Proposed new value.
        policy: Approval policy to enforce (defaults to STANDARD).

    Returns:
        str | None: Approval request message if approval is required, otherwise None.
    """
    gate = ApprovalGate(policy=policy, operation=operation, target=target)
    if gate.requires_approval(current_value, current_origin):
        return gate.format_request(
            reason="Field is human-authored",
            old_value=current_value,
            new_value=proposed_value,
        )
    return None
