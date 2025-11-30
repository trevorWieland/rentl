"""Shared glossary tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def search_glossary(context: ProjectContext, term_src: str) -> str:
    """Search for a glossary entry by source term.

    Returns:
        str: Glossary entry details or "not found" message.
    """
    logger.info("Tool call: search_glossary(term_src=%s)", term_src)
    for entry in context.glossary:
        if entry.term_src == term_src:
            parts = [
                f"Term (source): {entry.term_src}",
                f"Term (target): {entry.term_tgt or '(not set)'}",
                f"Notes: {entry.notes or '(not set)'}",
            ]
            return "\n".join(parts)
    return f"No glossary entry found for '{term_src}'"


def read_glossary_entry(context: ProjectContext, term_src: str) -> str:
    """Return a specific glossary entry if present."""
    logger.info("Tool call: read_glossary_entry(term_src=%s)", term_src)
    for entry in context.glossary:
        if entry.term_src == term_src:
            parts = [
                f"Term (source): {entry.term_src}",
                f"Term (target): {entry.term_tgt or '(not set)'}",
                f"Notes: {entry.notes or '(not set)'}",
            ]
            return "\n".join(parts)
    return f"No glossary entry found for '{term_src}'"


async def add_glossary_entry(context: ProjectContext, term_src: str, term_tgt: str, notes: str | None = None) -> str:
    """Add a new glossary entry.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    logger.info("Tool call: add_glossary_entry(term_src=%s)", term_src)
    origin = f"agent:glossary_curator:{date.today().isoformat()}"
    result = await context.add_glossary_entry(term_src=term_src, term_tgt=term_tgt, notes=notes, origin=origin)
    return result


async def update_glossary_entry(
    context: ProjectContext, term_src: str, term_tgt: str | None = None, notes: str | None = None
) -> str:
    """Update an existing glossary entry.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    logger.info("Tool call: update_glossary_entry(term_src=%s)", term_src)
    existing_entry = next((entry for entry in context.glossary if entry.term_src == term_src), None)
    if existing_entry:
        if term_tgt is not None:
            approval = request_if_human_authored(
                operation="update",
                target=f"glossary.{term_src}.term_tgt",
                current_value=existing_entry.term_tgt,
                current_origin=existing_entry.term_tgt_origin,
                proposed_value=term_tgt,
            )
            if approval:
                return approval
        if notes is not None:
            approval = request_if_human_authored(
                operation="update",
                target=f"glossary.{term_src}.notes",
                current_value=existing_entry.notes,
                current_origin=existing_entry.notes_origin,
                proposed_value=notes,
            )
            if approval:
                return approval

    origin = f"agent:glossary_curator:{date.today().isoformat()}"
    result = await context.update_glossary_entry(term_src=term_src, term_tgt=term_tgt, notes=notes, origin=origin)
    return result


async def delete_glossary_entry(context: ProjectContext, term_src: str) -> str:
    """Delete a glossary entry if it exists.

    Returns:
        str: Status message indicating deletion or not-found.
    """
    logger.info("Tool call: delete_glossary_entry(term_src=%s)", term_src)
    return await context.delete_glossary_entry(term_src)
