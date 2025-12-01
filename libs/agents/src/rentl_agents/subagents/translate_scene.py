"""Scene translation subagent."""

from __future__ import annotations

from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.backends.mtl import is_mtl_available
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.hitl.invoke import Decision, run_with_human_loop
from rentl_agents.tools.scene import scene_read_overview
from rentl_agents.tools.translation import (
    styleguide_read_full,
    translation_check_mtl_available,
    translation_create_line,
    translation_create_mtl_suggestion,
    ui_read_settings,
)

logger = get_logger(__name__)


class SceneTranslationResult(BaseModel):
    """Result structure from scene translator subagent."""

    scene_id: str = Field(description="Scene identifier that was translated.")
    lines_translated: int = Field(description="Number of lines translated in this scene.")


def build_translator_system_prompt(source_lang: str, target_lang: str) -> str:
    """Build language-agnostic translator system prompt.

    Args:
        source_lang: Source language code (e.g., "jpn", "eng").
        target_lang: Target language code (e.g., "eng", "spa").

    Returns:
        str: System prompt configured for the language pair.
    """
    return f"""You are a professional visual novel translator specializing in {source_lang.upper()}→{target_lang.upper()} translation.

    Your goal is to produce natural, accurate, and context-aware translations that preserve the
    original meaning, tone, and character voices. You have access to:

    - Character metadata (names, pronouns, speech patterns)
    - Glossary entries (canonical terminology)
    - Style guide (localization guidelines)
    - Scene context (summaries, tags, primary characters)
    - UI constraints (line length, wrapping rules)

    You also have access to two translation approaches:

1. **MTL Translation Tool (translation_create_mtl_suggestion)**: A specialized translation model fine-tuned for
   visual novel translation. Use this for initial translations or when you want assistance
   with difficult phrases. The MTL output should be reviewed and may need refinement.

2. **Direct Translation**: You can translate lines yourself using your understanding of context,
   character voices, and localization best practices.

**Translation Workflow:**
1. Read scene overview to understand context, characters, and mood
2. For each line:
   - Consider speaker, emotional tone, and context
   - Optionally call translation_create_mtl_suggestion for assistance
   - Review and refine the translation as needed
   - Call styleguide_read_full and ui_read_settings if you need guidance on style/length
   - Call translation_create_line with your final translation
3. Maintain consistency with glossary and character voices
4. Follow style guide preferences (honorifics, idioms, references)

**Important:**
- Always translate into natural {target_lang.upper()}
- Preserve speaker personality and speech patterns
- Use glossary terms consistently
- Don't blindly accept MTL output - review and refine it
- Translate each line exactly once
- End the conversation when all lines are translated
"""


async def translate_scene(
    context: ProjectContext,
    scene_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> SceneTranslationResult:
    """Run the scene translation agent for *scene_id* and return translation statistics.

    Args:
        context: Project context with metadata.
        scene_id: Scene identifier to translate.
        allow_overwrite: Allow overwriting existing translations.
        decision_handler: Optional callback to resolve HITL interrupts.
        thread_id: Optional thread identifier for resumable runs.
        checkpointer: Optional LangGraph checkpointer (defaults to SQLite if configured).

    Returns:
        SceneTranslationResult: Translation statistics for this scene.

    Notes:
        This function creates a translation agent that can use either direct translation
        or the MTL backend (if configured). The agent reviews MTL output and refines it
        before writing final translations to disk.
    """
    logger.info("Translating scene %s", scene_id)

    lines = await context.load_scene_lines(scene_id)
    await context._load_translations(scene_id)
    pre_count = context.get_translated_line_count(scene_id)
    line_count = len(lines)

    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_scene_translator_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    # Check MTL availability
    user_prompt = build_scene_translator_user_prompt(context, scene_id, lines=lines)

    logger.debug("Scene translator prompt for %s:\n%s", scene_id, user_prompt)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'translate'}:{scene_id}",
    )

    # Return translation statistics
    post_count = context.get_translated_line_count(scene_id)
    delta = max(post_count - pre_count, 0)
    result = SceneTranslationResult(
        scene_id=scene_id,
        lines_translated=delta or line_count,
    )

    logger.info("Scene %s translation complete: %d lines", scene_id, line_count)
    return result


def create_scene_translator_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create scene translator LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for scene translation.
    """
    tools = _build_scene_translator_tools(context, allow_overwrite=allow_overwrite, agent_name="scene_translator")
    model = get_default_chat_model()
    system_prompt = build_translator_system_prompt(context.game.source_lang, context.game.target_lang)

    interrupt_on = {
        "translation_create_line": True,
    }
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )

    return graph


def build_scene_translator_user_prompt(context: ProjectContext, scene_id: str, *, lines: list | None = None) -> str:
    """Construct the user prompt for the scene translator using live context.

    Returns:
        str: User prompt content to send to the translator subagent.
    """
    target_lang = context.game.target_lang
    src_lang = context.game.source_lang
    scene_meta = context.get_scene(scene_id)
    line_list = lines if lines is not None else []
    line_count = len(line_list)
    characters = (
        ", ".join(scene_meta.annotations.primary_characters) if scene_meta.annotations.primary_characters else "unknown"
    )
    mtl_status = "MTL backend is available" if is_mtl_available() else "MTL backend not configured"

    return f"""Translate this scene to {target_lang.upper()}.

Scene: {scene_id}
Title: {scene_meta.title or "Untitled"}
Characters: {characters}
Lines to translate: {line_count}
Source Language: {src_lang.upper()}
Target Language: {target_lang.upper()}
{mtl_status}

Instructions:
1. Read the scene overview to understand context
2. Translate each line maintaining speaker personality and tone
3. You may use translation_create_mtl_suggestion for assistance, but review and refine the output
4. Call styleguide_read_full and ui_read_settings if you need format/style constraints
5. Call translation_create_line(scene_id, line_id, source_text, target_text) for each line with your final translation
6. Ensure all {line_count} lines are translated
7. End the conversation when complete

Begin translation now."""


def _build_scene_translator_tools(context: ProjectContext, *, allow_overwrite: bool, agent_name: str) -> list[BaseTool]:
    """Return tools for the scene translator subagent bound to the shared context."""
    written_line_ids: set[str] = set()

    @tool("scene_read_overview")
    async def read_scene_tool(scene_id: str) -> str:
        """Return scene metadata and transcript for translation context."""
        return await scene_read_overview(context, scene_id)

    @tool("translation_create_mtl_suggestion")
    async def mtl_translate_tool(line_id: str, source_text: str, context_lines: list[str] | None = None) -> str:
        """Call specialized MTL model for translation.

        Returns:
            str: Translated text or an error message.
        """
        return await translation_create_mtl_suggestion(line_id, source_text, context_lines)

    @tool("translation_create_line")
    async def write_translation_tool(scene_id: str, line_id: str, source_text: str, target_text: str) -> str:
        """Write a translation for a line with provenance tracking.

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
            allow_overwrite=allow_overwrite,
            written_line_ids=written_line_ids,
        )

    @tool("styleguide_read_full")
    async def read_style_guide_tool() -> str:
        """Return the project style guide content."""
        return await styleguide_read_full(context)

    @tool("ui_read_settings")
    def get_ui_settings_tool() -> str:
        """Return UI constraints from game metadata."""
        return ui_read_settings(context)

    @tool("translation_check_mtl_available")
    def check_mtl_available_tool() -> str:
        """Check if MTL backend is configured and available.

        Returns:
            str: Status message indicating MTL availability.
        """
        return translation_check_mtl_available()

    return [
        read_scene_tool,
        mtl_translate_tool,
        write_translation_tool,
        read_style_guide_tool,
        get_ui_settings_tool,
        check_mtl_available_tool,
    ]
