"""Utilities for constructing DeepAgents graphs."""

from __future__ import annotations

from deepagents import create_deep_agent
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.scene import build_scene_tools

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant summarizing scenes for reference.
Always read the scene overview, ensure you understand the emotional beats, and
produce concise summaries (1-2 sentences) that mention key characters by name.
When finished, call the write_scene_summary tool with your final summary.

Be sure to write summaries in the same language as the source text.
"""


async def summarize_scene(context: ProjectContext, scene_id: str, *, allow_overwrite: bool = False) -> str:
    """Run the scene summarization agent for *scene_id* and return the summary.

    Returns:
        str: Summary text stored for the scene (empty if skipped).
    """
    logger.info("Summarizing scene %s", scene_id)
    lines = await context.load_scene_lines(scene_id)
    tools = build_scene_tools(context, scene_id, lines, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    agent = create_deep_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)

    source_lang = context.game.source_lang.upper()
    user_prompt = (
        "Summarize the current scene. Be concise and cover mood, conflicts, and outcomes. "
        f"Write the final summary in the source language ({source_lang}). "
        "Always call write_scene_summary exactly once with your final summary. "
        "Once you have written the summary successfully, end the conversation."
    )
    await agent.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})
    updated_scene = context.get_scene(scene_id)
    summary = updated_scene.annotations.summary or ""
    logger.info("Scene %s summary stored (%d chars)", scene_id, len(summary))
    return summary
