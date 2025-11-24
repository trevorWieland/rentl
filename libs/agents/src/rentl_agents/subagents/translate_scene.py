"""Scene translation subagent."""

from __future__ import annotations

from deepagents import CompiledSubAgent
from langchain.agents import create_agent
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.backends.mtl import is_mtl_available
from rentl_agents.tools.translation import build_translation_tools

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

1. **MTL Translation Tool (mtl_translate)**: A specialized translation model fine-tuned for
   visual novel translation. Use this for initial translations or when you want assistance
   with difficult phrases. The MTL output should be reviewed and may need refinement.

2. **Direct Translation**: You can translate lines yourself using your understanding of context,
   character voices, and localization best practices.

**Translation Workflow:**
1. Read scene overview to understand context, characters, and mood
2. For each line:
   - Consider speaker, emotional tone, and context
   - Optionally call mtl_translate for assistance
   - Review and refine the translation as needed
   - Call read_style_guide and get_ui_settings if you need guidance on style/length
   - Call write_translation with your final translation
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
) -> SceneTranslationResult:
    """Run the scene translation agent for *scene_id* and return translation statistics.

    Args:
        context: Project context with metadata.
        scene_id: Scene identifier to translate.
        allow_overwrite: Allow overwriting existing translations.

    Returns:
        SceneTranslationResult: Translation statistics for this scene.

    Notes:
        This function creates a translation agent that can use either direct translation
        or the MTL backend (if configured). The agent reviews MTL output and refines it
        before writing final translations to disk.
    """
    logger.info("Translating scene %s", scene_id)

    # Get language pair from game metadata
    target_lang = context.game.target_lang

    lines = await context.load_scene_lines(scene_id)
    await context._load_translations(scene_id)
    pre_count = context.get_translated_line_count(scene_id)

    subagent = create_scene_translator_subagent(context, allow_overwrite=allow_overwrite)
    runnable = subagent["runnable"]

    # Check MTL availability
    mtl_status = "MTL backend is available" if is_mtl_available() else "MTL backend not configured"

    # Build user prompt with line information
    line_count = len(lines)
    scene_meta = context.get_scene(scene_id)
    characters = (
        ", ".join(scene_meta.annotations.primary_characters) if scene_meta.annotations.primary_characters else "unknown"
    )

    user_prompt = f"""Translate this scene to {target_lang.upper()}.

Scene: {scene_id}
Title: {scene_meta.title or "Untitled"}
Characters: {characters}
Lines to translate: {line_count}
{mtl_status}

Instructions:
1. Read the scene overview to understand context
2. Translate each line maintaining speaker personality and tone
3. You may use mtl_translate for assistance, but review and refine the output
4. Call read_style_guide and get_ui_settings if you need format/style constraints
5. Call write_translation(scene_id, line_id, source_text, target_text) for each line with your final translation
6. Ensure all {line_count} lines are translated
7. End the conversation when complete

Begin translation now."""

    logger.debug("Scene translator prompt for %s:\n%s", scene_id, user_prompt)
    await runnable.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})

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
    name: str | None = None,
) -> CompiledSubAgent:
    """Create scene translator LangChain subagent.

    Returns:
        CompiledSubAgent: Configured scene translator agent.
    """
    tools = build_translation_tools(context, agent_name="scene_translator", allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    system_prompt = build_translator_system_prompt(context.game.source_lang, context.game.target_lang)

    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    return CompiledSubAgent(
        name=name or "scene-translator",
        description="Translates a scene with context-aware JP→EN handling and optional MTL assistance",
        runnable=graph,
    )
