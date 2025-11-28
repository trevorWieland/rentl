"""HITL approval system with provenance-based gating.

This module provides the approval framework for rentl agents, enabling intelligent
human-in-the-loop controls based on provenance tracking (*_origin fields).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum

ProvenanceValue = str | list[str] | None
ProvenanceEntry = Mapping[str, str | None]


class ApprovalPolicy(StrEnum):
    """Approval policy for tool operations.

    Policies:
        PERMISSIVE: Never require approval (for safe, read-only, or additive operations).
        STANDARD: Check provenance - require approval only if overwriting human data.
        STRICT: Always require approval before executing.
    """

    PERMISSIVE = "permissive"
    STANDARD = "standard"
    STRICT = "strict"


def is_human_authored(origin: str | None) -> bool:
    """Check if a provenance origin indicates human authorship.

    Args:
        origin: Provenance string from a *_origin field.

    Returns:
        bool: True if the field was authored by a human, False otherwise.

    Examples:
        >>> is_human_authored("human")
        True
        >>> is_human_authored("agent:scene_detailer:2024-11-22")
        False
        >>> is_human_authored(None)
        False
    """
    return origin == "human"


def is_agent_authored(origin: str | None) -> bool:
    """Check if a provenance origin indicates agent authorship.

    Args:
        origin: Provenance string from a *_origin field.

    Returns:
        bool: True if the field was authored by an agent, False otherwise.

    Examples:
        >>> is_agent_authored("agent:scene_detailer:2024-11-22")
        True
        >>> is_agent_authored("human")
        False
        >>> is_agent_authored(None)
        False
    """
    if origin is None:
        return False
    return origin.startswith("agent:")


def check_field_approval(
    field_value: ProvenanceValue,
    field_origin: str | None,
    policy: ApprovalPolicy = ApprovalPolicy.STANDARD,
) -> bool:
    """Check if approval is needed to update a field based on provenance.

    Args:
        field_value: Current value of the field being updated.
        field_origin: Provenance string for the field (*_origin).
        policy: Approval policy to apply.

    Returns:
        bool: True if approval is required, False if operation can proceed.

    Examples:
        >>> check_field_approval("Aya", "human", ApprovalPolicy.STANDARD)
        True
        >>> check_field_approval("Summary", "agent:scene_detailer:2024-11-22", ApprovalPolicy.STANDARD)
        False
        >>> check_field_approval(None, None, ApprovalPolicy.STANDARD)
        False
        >>> check_field_approval("Aya", "human", ApprovalPolicy.PERMISSIVE)
        False
        >>> check_field_approval("Aya", None, ApprovalPolicy.STRICT)
        True
    """
    if policy == ApprovalPolicy.PERMISSIVE:
        return False

    if policy == ApprovalPolicy.STRICT:
        return True

    # STANDARD policy: check provenance
    # Empty/null field -> no approval needed
    if field_value is None or (isinstance(field_value, (list, str)) and len(field_value) == 0):
        return False

    # Human-authored field -> require approval
    # Agent-authored or no origin -> allow update
    return is_human_authored(field_origin)


def check_entry_approval(
    entry: ProvenanceEntry,
    origin_fields: Sequence[str],
    policy: ApprovalPolicy = ApprovalPolicy.STANDARD,
) -> bool:
    """Check if approval is needed to delete an entry based on provenance.

    Args:
        entry: Dictionary representing the entry to delete.
        origin_fields: List of *_origin field names to check.
        policy: Approval policy to apply.

    Returns:
        bool: True if approval is required, False if deletion can proceed.

    Examples:
        >>> entry = {"name_tgt": "Aya", "name_tgt_origin": "human", "notes": "", "notes_origin": None}
        >>> check_entry_approval(entry, ["name_tgt_origin", "notes_origin"], ApprovalPolicy.STANDARD)
        True
        >>> entry = {"summary": "Scene summary", "summary_origin": "agent:scene_detailer:2024-11-22"}
        >>> check_entry_approval(entry, ["summary_origin"], ApprovalPolicy.STANDARD)
        False
        >>> check_entry_approval(entry, ["summary_origin"], ApprovalPolicy.STRICT)
        True
    """
    if policy == ApprovalPolicy.PERMISSIVE:
        return False

    if policy == ApprovalPolicy.STRICT:
        return True

    # STANDARD policy: check if ANY field is human-authored
    for origin_field in origin_fields:
        origin = entry.get(origin_field)
        # Type narrowing: origin fields should be str | None
        if (origin is None or isinstance(origin, str)) and is_human_authored(origin):
            return True

    return False


def format_approval_request(
    operation: str,
    target: str,
    reason: str,
    old_value: ProvenanceValue = None,
    new_value: ProvenanceValue = None,
) -> str:
    """Format a concise, single-line approval request message.

    Returns:
        str: Human-readable approval prompt including reason and value changes.
    """
    current_display = f" current={old_value!r}" if old_value is not None else ""
    proposed_display = f" -> proposed={new_value!r}" if new_value is not None else ""
    return f"APPROVAL REQUIRED: {operation} {target} ({reason}){current_display}{proposed_display}"


class ApprovalGate:
    """Context manager for approval-gated operations.

    This class provides a reusable pattern for implementing HITL approval
    in agent tools. It checks provenance and raises interrupts when needed.

    Examples:
        >>> # In a tool implementation:
        >>> async def update_character_name(character_id: str, new_name: str):
        ...     char = get_character(character_id)
        ...     gate = ApprovalGate(
        ...         policy=ApprovalPolicy.STANDARD,
        ...         operation="update",
        ...         target=f"character.{character_id}.name_tgt"
        ...     )
        ...     if gate.requires_approval(char.name_tgt, char.name_tgt_origin):
        ...         request = gate.format_request(
        ...             reason="Field is human-authored",
        ...             old_value=char.name_tgt,
        ...             new_value=new_name
        ...         )
        ...         # In DeepAgents, this would trigger an interrupt
        ...         # For now, we just return the request message
        ...         return request
        ...     # Proceed with update
        ...     char.name_tgt = new_name
        ...     char.name_tgt_origin = "agent:character_detailer:2024-11-22"
        ...     return "Updated successfully"
    """

    def __init__(
        self,
        policy: ApprovalPolicy,
        operation: str,
        target: str,
    ) -> None:
        """Initialize the approval gate.

        Args:
            policy: Approval policy to enforce.
            operation: Type of operation (e.g., "update", "delete").
            target: Target identifier (e.g., "character.aya.name_tgt").
        """
        self.policy = policy
        self.operation = operation
        self.target = target

    def requires_approval(
        self,
        field_value: ProvenanceValue = None,
        field_origin: str | None = None,
        entry: ProvenanceEntry | None = None,
        origin_fields: Sequence[str] | None = None,
    ) -> bool:
        """Check if approval is required for the operation.

        Args:
            field_value: Current field value (for field-level checks).
            field_origin: Provenance for the field (for field-level checks).
            entry: Entry dictionary (for entry-level checks).
            origin_fields: List of origin field names (for entry-level checks).

        Returns:
            bool: True if approval is required, False otherwise.
        """
        if entry is not None and origin_fields is not None:
            return check_entry_approval(entry, origin_fields, self.policy)

        return check_field_approval(field_value, field_origin, self.policy)

    def format_request(
        self,
        reason: str,
        old_value: ProvenanceValue = None,
        new_value: ProvenanceValue = None,
    ) -> str:
        """Format an approval request message.

        Args:
            reason: Explanation of why approval is needed.
            old_value: Current/old value (optional).
            new_value: Proposed new value (optional).

        Returns:
            str: Formatted approval request.
        """
        return format_approval_request(
            operation=self.operation,
            target=self.target,
            reason=reason,
            old_value=old_value,
            new_value=new_value,
        )
