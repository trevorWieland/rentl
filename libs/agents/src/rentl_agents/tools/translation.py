"""Shared translation tool implementations."""

from __future__ import annotations

from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage
from rentl_core.context.project import ProjectContext
from rentl_core.model.line import TranslatedLine
from rentl_core.util.logging import get_logger

from rentl_agents.backends.mtl import get_mtl_chat_model, get_mtl_system_prompt, is_mtl_available
from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


async def translation_create_mtl_suggestion(
    line_id: str, source_text: str, context_lines: list[str] | None = None
) -> str:
    """Call specialized MTL model for translation.

    Returns:
        str: Translated text or an error message.
    """
    if not is_mtl_available():
        return "ERROR: MTL backend not configured. Set MTL_URL and MTL_MODEL environment variables."

    mtl_model = get_mtl_chat_model()
    if not mtl_model:
        return "ERROR: Failed to initialize MTL model."

    messages = [SystemMessage(content=get_mtl_system_prompt())]

    if context_lines:
        context_str = "\n".join(context_lines[-10:])
        prompt = f"Context (previous lines):\n{context_str}\n\nTranslate this line:\n{source_text}"
    else:
        prompt = f"Translate this line:\n{source_text}"

    messages.append(HumanMessage(content=prompt))

    logger.debug("Calling MTL model for line %s", line_id)
    response = await mtl_model.ainvoke(messages)
    translation = response.content.strip() if isinstance(response.content, str) else str(response.content)
    logger.debug("MTL translation for %s: %s", line_id, translation)
    return translation


async def translation_create_line(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    source_text: str,
    target_text: str,
    *,
    agent_name: str,
    allow_overwrite: bool,
    written_line_ids: set[str],
) -> str:
    """Write a translation for a line with provenance tracking.

    Returns:
        str: Confirmation message or approval request.
    """
    if line_id in written_line_ids:
        return f"ERROR: Line {line_id} already written in this session. Provide a final assistant response."

    origin = f"agent:{agent_name}:{date.today().isoformat()}"

    existing = next((t for t in await context.get_translations(scene_id) if t.id == line_id), None)
    if existing:
        approval = request_if_human_authored(
            operation="update",
            target=f"translation.{scene_id}.{line_id}",
            current_value=existing.text_tgt,
            current_origin=existing.text_tgt_origin,
            proposed_value=target_text,
        )
        if approval:
            return approval

    logger.info("Tool call: translation_create_line(scene_id=%s, line_id=%s)", scene_id, line_id)
    translated_line = TranslatedLine(
        id=line_id,
        text_src=source_text,
        text_tgt=target_text,
        text_tgt_origin=origin,
    )

    result = await context.record_translation(
        scene_id,
        translated_line,
        allow_overwrite=allow_overwrite,
    )
    written_line_ids.add(line_id)
    return result


async def translation_update_line(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    source_text: str,
    target_text: str,
    *,
    agent_name: str,
    written_line_ids: set[str],
) -> str:
    """Overwrite a translation for a line with provenance tracking.

    Returns:
        str: Confirmation message or approval request.
    """
    return await translation_create_line(
        context,
        scene_id,
        line_id,
        source_text,
        target_text,
        agent_name=agent_name,
        allow_overwrite=True,
        written_line_ids=written_line_ids,
    )


async def styleguide_read_full(context: ProjectContext) -> str:
    """Return the project style guide content.

    Returns:
        str: Style guide content or fallback text.
    """
    return await context.read_style_guide()


def ui_read_settings(context: ProjectContext) -> str:
    """Return UI constraints from game metadata.

    Returns:
        str: UI settings formatted as lines.
    """
    ui = context.get_ui_config()
    if not ui:
        return "No UI settings configured."
    return "\n".join(f"{k}: {v}" for k, v in ui.items())


def translation_check_mtl_available() -> str:
    """Check if MTL backend is configured and available.

    Returns:
        str: Status message indicating MTL availability.
    """
    if is_mtl_available():
        from rentl_core.config.settings import get_settings

        settings = get_settings()
        model = settings.mtl_model or "configured"
        return f"MTL backend is available (model: {model})"
    return "MTL backend is not configured. Use direct translation instead."
