"""Shared glossary tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def glossary_search_term(context: ProjectContext, term_src: str) -> str:
    """Search for a glossary entry by source term.

    Returns:
        str: Glossary entry details or "not found" message.
    """
    logger.info("Tool call: glossary_search_term(term_src=%s)", term_src)
    for entry in context.glossary:
        if entry.term_src == term_src:
            parts = [
                f"Term (source): {entry.term_src}",
                f"Term (target): {entry.term_tgt or '(not set)'}",
                f"Notes: {entry.notes or '(not set)'}",
            ]
            return "\n".join(parts)
    return f"No glossary entry found for '{term_src}'"


def glossary_read_entry(context: ProjectContext, term_src: str) -> str:
    """Return a specific glossary entry if present."""
    logger.info("Tool call: glossary_read_entry(term_src=%s)", term_src)
    for entry in context.glossary:
        if entry.term_src == term_src:
            parts = [
                f"Term (source): {entry.term_src}",
                f"Term (target): {entry.term_tgt or '(not set)'}",
                f"Notes: {entry.notes or '(not set)'}",
            ]
            return "\n".join(parts)
    return f"No glossary entry found for '{term_src}'"


async def glossary_create_entry(context: ProjectContext, term_src: str, term_tgt: str, notes: str | None = None) -> str:
    """Add a new glossary entry.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    logger.info("Tool call: glossary_create_entry(term_src=%s)", term_src)
    origin = f"agent:meta_glossary_curator:{date.today().isoformat()}"
    result = await context.add_glossary_entry(term_src=term_src, term_tgt=term_tgt, notes=notes, origin=origin)
    return result


async def glossary_update_entry(
    context: ProjectContext, term_src: str, term_tgt: str | None = None, notes: str | None = None
) -> str:
    """Update an existing glossary entry.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    logger.info("Tool call: glossary_update_entry(term_src=%s)", term_src)
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

    origin = f"agent:meta_glossary_curator:{date.today().isoformat()}"
    result = await context.update_glossary_entry(term_src=term_src, term_tgt=term_tgt, notes=notes, origin=origin)
    return result


async def glossary_delete_entry(context: ProjectContext, term_src: str) -> str:
    """Delete a glossary entry if it exists.

    Returns:
        str: Status message indicating deletion or not-found.
    """
    logger.info("Tool call: glossary_delete_entry(term_src=%s)", term_src)
    return await context.delete_glossary_entry(term_src)


async def glossary_merge_entries(context: ProjectContext, source_term: str, target_term: str) -> str:
    """Merge a duplicate glossary entry into a target entry with basic note preservation.

    Returns:
        str: Status or approval message.
    """
    logger.info("Tool call: glossary_merge_entries(source=%s, target=%s)", source_term, target_term)
    source = next((e for e in context.glossary if e.term_src == source_term), None)
    target = next((e for e in context.glossary if e.term_src == target_term), None)

    if not source:
        return f"Source glossary entry '{source_term}' not found."
    if not target:
        return f"Target glossary entry '{target_term}' not found."
    if source_term == target_term:
        return "Source and target terms are the same; nothing to merge."

    if any(
        origin == "human"
        for origin in (
            source.term_src_origin,
            source.term_tgt_origin,
            source.notes_origin,
            target.term_src_origin,
            target.term_tgt_origin,
            target.notes_origin,
        )
    ):
        return (
            f"APPROVAL REQUIRED to merge glossary entry '{source_term}' into '{target_term}' "
            "because one or more fields are human-authored."
        )

    combined_notes = target.notes or ""
    if source.notes:
        combined_notes = f"{combined_notes}\nMerged from {source_term}: {source.notes}".strip()

    target.term_tgt = target.term_tgt or source.term_tgt
    target.term_tgt_origin = target.term_tgt_origin or source.term_tgt_origin
    target.notes = combined_notes or None
    target.notes_origin = target.notes_origin or source.notes_origin

    await context.delete_glossary_entry(source_term)
    await context._write_glossary()
    return f"Merged glossary entry '{source_term}' into '{target_term}'"
