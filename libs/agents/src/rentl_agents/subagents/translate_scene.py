"""Scene translation subagent."""

from __future__ import annotations

from deepagents import create_deep_agent
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.backends.mtl import is_mtl_available
from rentl_agents.tools.translation import build_translation_tools

logger = get_logger(__name__)


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
) -> dict[str, str]:
    """Run the scene translation agent for *scene_id* and return translations.

    Args:
        context: Project context with metadata.
        scene_id: Scene identifier to translate.

    Returns:
        dict[str, str]: Mapping of line IDs to translated text.

    Notes:
        This function creates a translation agent that can use either direct translation
        or the MTL backend (if configured). The agent reviews MTL output and refines it
        before writing final translations.
    """
    logger.info("Translating scene %s", scene_id)

    # Get language pair from game metadata
    source_lang = context.game.source_lang
    target_lang = context.game.target_lang

    lines = await context.load_scene_lines(scene_id)
    tools = build_translation_tools(context, scene_id, agent_name="scene_translator")
    model = get_default_chat_model()

    # Build language-aware system prompt
    system_prompt = build_translator_system_prompt(source_lang, target_lang)
    agent = create_deep_agent(model=model, tools=tools, system_prompt=system_prompt)

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
4. Call write_translation for each line with your final translation
5. Ensure all {line_count} lines are translated
6. End the conversation when complete

Begin translation now."""

    await agent.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})

    # TODO: Collect translations from agent execution
    # For now, return empty dict (translations are logged in tools)
    logger.info("Scene %s translation complete", scene_id)
    return {}
