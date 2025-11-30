"""Scene detailer subagent.

This subagent generates comprehensive scene metadata including summaries, tags,
primary characters, and locations by analyzing scene content.
"""

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
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.hitl.invoke import Decision, run_with_human_loop
from rentl_agents.tools.context_docs import list_context_docs, read_context_doc
from rentl_agents.tools.scene import (
    read_scene,
    read_scene_overview,
    write_primary_characters,
    write_scene_locations,
    write_scene_summary,
    write_scene_tags,
)


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
- Write summaries, tags, and location names in the source language (same as scene text)
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

    user_prompt = build_scene_detailer_user_prompt(context, scene_id, line_count=len(lines))

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
    tools = _build_scene_detailer_tools(context, allow_overwrite=allow_overwrite)
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


def build_scene_detailer_user_prompt(context: ProjectContext, scene_id: str, *, line_count: int | None = None) -> str:
    """Construct the user prompt for the scene detailer using live project context.

    Args:
        context: Shared project context.
        scene_id: Target scene identifier.
        line_count: Optional precomputed line count (falls back to loaded scene length).

    Returns:
        str: The user prompt supplied to the scene detailer agent.
    """
    line_total: int | str = line_count if line_count is not None else "unknown"
    source_lang = context.game.source_lang.upper()
    location_ids = ", ".join(sorted(context.locations.keys()))
    character_ids = ", ".join(sorted(context.characters.keys()))

    return f"""Analyze this scene and generate complete metadata.

Scene ID: {scene_id}
Lines: {line_total}
Source Language: {source_lang}

Instructions:
1. Read the scene overview (shows existing metadata if any)
2. Analyze the full transcript
3. Write summary in {source_lang} (1-2 sentences covering mood, key events, outcomes) using write_scene_summary(scene_id, summary)
4. Write tags in {source_lang} (3-6 quick descriptive tags)
5. Write primary_characters (character IDs from speakers and context) using write_primary_characters(scene_id, ids). Available characters: {character_ids}
6. Write scene_locations (location IDs inferred from setting/context) using write_scene_locations(scene_id, ids) and keep names in {source_lang}. Available locations: {location_ids}
7. End conversation when all 4 metadata types are recorded

Begin analysis now."""


def _build_scene_detailer_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the scene detailer subagent bound to the shared context."""
    written_summary: set[str] = set()
    written_tags: set[str] = set()
    written_characters: set[str] = set()
    written_locations: set[str] = set()
    context_doc_tools = _build_context_doc_tools(context)

    @tool("read_scene")
    async def read_scene_tool(scene_id: str) -> str:
        """Return metadata and transcript for the scene (no redactions)."""
        return await read_scene(context, scene_id)

    @tool("read_scene_overview")
    async def read_scene_overview_tool(scene_id: str) -> str:
        """Return metadata and transcript for the scene (with existing summary if allowed)."""
        return await read_scene_overview(context, scene_id, allow_overwrite=allow_overwrite)

    @tool("write_scene_summary")
    async def write_scene_summary_tool(scene_id: str, summary: str) -> str:
        """Store the final summary for this scene.

        Returns:
            str: Confirmation or approval message.
        """
        return await write_scene_summary(context, scene_id, summary, written_summary=written_summary)

    @tool("write_scene_tags")
    async def write_scene_tags_tool(scene_id: str, tags: list[str]) -> str:
        """Store tags for this scene.

        Returns:
            str: Confirmation or approval message.
        """
        return await write_scene_tags(context, scene_id, tags, written_tags=written_tags)

    @tool("write_primary_characters")
    async def write_primary_characters_tool(scene_id: str, character_ids: list[str]) -> str:
        """Store primary characters identified in this scene.

        Returns:
            str: Confirmation or approval message.
        """
        return await write_primary_characters(context, scene_id, character_ids, written_characters=written_characters)

    @tool("write_scene_locations")
    async def write_scene_locations_tool(scene_id: str, location_ids: list[str]) -> str:
        """Store locations identified in this scene.

        Returns:
            str: Confirmation or approval message.
        """
        return await write_scene_locations(context, scene_id, location_ids, written_locations=written_locations)

    return [
        read_scene_tool,
        read_scene_overview_tool,
        *context_doc_tools,
        write_scene_summary_tool,
        write_scene_tags_tool,
        write_primary_characters_tool,
        write_scene_locations_tool,
    ]


def _build_context_doc_tools(context: ProjectContext) -> list[BaseTool]:
    """Return context doc tools for subagent use."""

    @tool("list_context_docs")
    async def list_context_docs_tool() -> str:
        """Return the available context document names."""
        return await list_context_docs(context)

    @tool("read_context_doc")
    async def read_context_doc_tool(filename: str) -> str:
        """Return the contents of a context document."""
        return await read_context_doc(context, filename)

    return [list_context_docs_tool, read_context_doc_tool]
