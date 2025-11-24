"""Tools for translation subagents."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.model.line import TranslatedLine
from rentl_core.util.logging import get_logger

from rentl_agents.backends.mtl import get_mtl_chat_model, get_mtl_system_prompt, is_mtl_available

logger = get_logger(__name__)


def build_translation_tools(
    context: ProjectContext,
    *,
    agent_name: str = "scene_translator",
    allow_overwrite: bool = False,
) -> list:
    """Construct translation tools usable across scenes.

    Args:
        context: Project context with metadata and translation state.
        agent_name: Name of the agent using these tools (for provenance).
        allow_overwrite: Allow overwriting existing translations.

    Returns:
        list: Tool callables ready to supply to translation agents.
    """
    from datetime import date

    # Track which lines have been written
    written_line_ids: set[str] = set()

    @tool("mtl_translate")
    async def mtl_translate(line_id: str, source_text: str, context_lines: list[str] | None = None) -> str:
        """Call specialized MTL model for translation.

        This tool sends source text to a specialized translation model (e.g., Sugoi-14B-Ultra)
        optimized for JP→EN translation. The model is fine-tuned for visual novel translation
        and can handle colloquial language, slang, and specialized vocabulary.

        Args:
            line_id: Line identifier for logging/tracking.
            source_text: Japanese source text to translate.
            context_lines: Optional list of preceding lines for context (recommended: ~10 lines).

        Returns:
            str: Translated English text from the MTL model.

        Notes:
            - The MTL model may require post-processing or refinement
            - This is a specialized tool; agents should review output before writing
            - Returns error message if MTL backend is not configured
        """
        if not is_mtl_available():
            return "ERROR: MTL backend not configured. Set MTL_URL and MTL_MODEL environment variables."

        mtl_model = get_mtl_chat_model()
        if not mtl_model:
            return "ERROR: Failed to initialize MTL model."

        # Build prompt with optional context
        messages = [SystemMessage(content=get_mtl_system_prompt())]

        if context_lines:
            # Include preceding lines for context
            context_str = "\n".join(context_lines[-10:])  # Limit to last 10 lines
            prompt = f"Context (previous lines):\n{context_str}\n\nTranslate this line:\n{source_text}"
        else:
            prompt = f"Translate this line:\n{source_text}"

        messages.append(HumanMessage(content=prompt))

        # Call MTL model
        logger.debug(f"Calling MTL model for line {line_id}")
        response = await mtl_model.ainvoke(messages)

        translation = response.content.strip() if isinstance(response.content, str) else str(response.content)
        logger.debug(f"MTL translation for {line_id}: {translation}")

        return translation

    @tool("write_translation")
    async def write_translation(scene_id: str, line_id: str, source_text: str, target_text: str) -> str:
        """Write a translation for a line with provenance tracking.

        This tool records the final translation for a line. It includes HITL approval
        gating based on provenance - if a line was previously translated by a human,
        approval will be required to overwrite it.

        Args:
            scene_id: Scene identifier owning the line.
            line_id: Stable line identifier (must match SourceLine.id).
            source_text: Original Japanese source text (for verification).
            target_text: Final English translation to record.

        Returns:
            str: Confirmation message or approval request.

        Notes:
            - This is a write-once tool per session - each line can only be written once
            - Provenance is automatically set to agent:{agent_name}:YYYY-MM-DD
            - Use this after reviewing MTL output or for direct translations
        """
        # Prevent duplicate writes in the same session
        if line_id in written_line_ids:
            return f"ERROR: Line {line_id} already written in this session. Provide a final assistant response."

        today = date.today().isoformat()
        origin = f"agent:{agent_name}:{today}"

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

        # Mark as written
        written_line_ids.add(line_id)

        return result

    tools = [mtl_translate, write_translation]

    @tool("read_style_guide")
    async def read_style_guide() -> str:
        """Return the project style guide content."""
        return await context.read_style_guide()

    @tool("get_ui_settings")
    def get_ui_settings() -> str:
        """Return UI constraints from game metadata."""
        ui = context.get_ui_config()
        if not ui:
            return "No UI settings configured."
        return "\n".join(f"{k}: {v}" for k, v in ui.items())

    tools.extend([read_style_guide, get_ui_settings])

    # Add MTL availability check tool for agents to query
    @tool("check_mtl_available")
    def check_mtl_available() -> str:
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

    tools.append(check_mtl_available)

    return tools
