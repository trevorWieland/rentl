"""Scene detailer subagent.

This subagent generates comprehensive scene metadata including summaries, tags,
primary characters, and locations by analyzing scene content.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.hitl.invoke import Decision, run_with_human_loop
from rentl_agents.tools.scene import build_scene_tools


class SceneDetailResult(BaseModel):
    """Result structure from scene detailer subagent."""

    summary: str = Field(description="Concise 1-2 sentence scene summary in source language.")
    tags: list[str] = Field(description="Quick descriptive tags for the scene (e.g., 'intro', 'conflict').")
    primary_characters: list[str] = Field(description="Character IDs of those who appear significantly.")
    locations: list[str] = Field(description="Location IDs where the scene takes place.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant analyzing scenes for metadata enrichment.

Your task is to read scene transcripts and generate comprehensive metadata:

1. **Summary**: A concise 1-2 sentence overview covering mood, key events, and outcomes
2. **Tags**: Quick descriptive tags (e.g., "intro", "conflict", "school", "emotional")
3. **Primary Characters**: Character IDs of those who appear or are mentioned significantly
4. **Locations**: Location IDs where the scene takes place

**Workflow:**
1. Read the scene overview to see existing metadata
2. Analyze the transcript carefully
3. Call write_scene_summary with your summary
4. Call write_scene_tags with appropriate tags (3-6 tags recommended)
5. Call write_primary_characters with character IDs (use speaker labels and context)
6. Call write_scene_locations with location IDs (infer from context if not explicit)
7. End the conversation once all metadata is recorded

**Important:**
- Write summaries in the source language (same as scene text)
- Use lowercase IDs for characters/locations (e.g., "mc", "aya", "school_rooftop")
- Be thorough but concise - capture essence without unnecessary detail
- Each write tool can only be called once per session
"""


async def detail_scene(
    context: ProjectContext,
    scene_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> SceneDetailResult:
    """Run the scene detailer agent for *scene_id* and return metadata.

    Args:
        context: Project context with metadata.
        scene_id: Scene identifier to detail.
        allow_overwrite: Allow overwriting existing metadata.
        decision_handler: Optional callback to resolve HITL interrupts.
        thread_id: Optional thread identifier for resumable runs.
        checkpointer: Optional LangGraph checkpointer (defaults to SQLite if configured).

    Returns:
        SceneDetailResult: Scene metadata with summary, tags, characters, locations.
    """
    logger.info("Detailing scene %s", scene_id)
    lines = await context.load_scene_lines(scene_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_scene_detailer_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    source_lang = context.game.source_lang.upper()
    line_count = len(lines)

    user_prompt = f"""Analyze this scene and generate complete metadata.

Scene ID: {scene_id}
Lines: {line_count}
Source Language: {source_lang}

Instructions:
1. Read the scene overview (shows existing metadata if any)
2. Analyze the full transcript
3. Write summary in {source_lang} (1-2 sentences covering mood, key events, outcomes) using write_scene_summary(scene_id, summary)
4. Write tags (3-6 quick descriptive tags)
5. Write primary_characters (character IDs from speakers and context) using write_primary_characters(scene_id, ids)
6. Write scene_locations (location IDs inferred from setting/context) using write_scene_locations(scene_id, ids)
7. End conversation when all 4 metadata types are recorded

Begin analysis now."""

    logger.debug("Scene detailer prompt for %s:\n%s", scene_id, user_prompt)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'scene-detail'}:{scene_id}",
    )

    # Retrieve updated scene metadata
    updated_scene = context.get_scene(scene_id)
    annotations = updated_scene.annotations

    result = SceneDetailResult(
        summary=annotations.summary or "",
        tags=annotations.tags,
        primary_characters=annotations.primary_characters,
        locations=annotations.locations,
    )

    logger.info(
        "Scene %s metadata: summary=%d chars, tags=%d, characters=%d, locations=%d",
        scene_id,
        len(result.summary),
        len(result.tags),
        len(result.primary_characters),
        len(result.locations),
    )

    return result


def create_scene_detailer_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create scene detailer LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for scene detailing.
    """
    tools = build_scene_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "write_scene_summary": True,
        "write_scene_tags": True,
        "write_primary_characters": True,
        "write_scene_locations": True,
    }
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )

    return graph
