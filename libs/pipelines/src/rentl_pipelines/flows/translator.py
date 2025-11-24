"""Translator pipeline for scene-by-scene translation.

This pipeline orchestrates the scene translator to produce aligned JP→EN translations
using enriched context from the Context Builder phase.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast

import anyio
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.backends.coordinator import create_coordinator_agent
from rentl_agents.subagents.translate_scene import create_scene_translator_subagent
from rentl_agents.tools.stats import build_stats_tools
from rentl_core.context.project import load_project_context
from rentl_core.util.logging import get_logger

from rentl_pipelines.flows.utils import SupportsAinvoke, invoke_with_interrupts

logger = get_logger(__name__)

_TRANSLATOR_SYSTEM_PROMPT = """You are the Translator coordinator.

Use task() to run the scene-translator subagent for each scene that needs translation.
Translate every target scene and ensure outputs are written via write_translation(scene_id, line_id, ...).
Use progress tools when helpful and stop when all scenes are complete."""


class TranslatorResult(BaseModel):
    """Results from the Translator pipeline."""

    scenes_translated: int = Field(description="Number of scenes translated.")
    lines_translated: int = Field(description="Total number of lines translated.")
    scenes_skipped: int = Field(description="Number of scenes skipped (already translated).")


async def _run_translator_async(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[str]] | None = None,
    thread_id: str | None = None,
) -> TranslatorResult:
    """Run the Translator pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to translate (default: all scenes).
        allow_overwrite: Allow overwriting existing translations.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.

    Returns:
        TranslatorResult: Statistics about what was translated.
    """
    logger.info("Starting Translator pipeline for %s", project_path)
    context = await load_project_context(project_path)

    # Determine which scenes to translate
    target_scene_ids = scene_ids if scene_ids else sorted(context.scenes.keys())
    logger.info("Target scenes: %d", len(target_scene_ids))

    # Filter scenes that already have translations unless overwrite
    output_dir = project_path / "output" / "translations"
    remaining_scene_ids: list[str] = []
    scenes_skipped = 0
    for sid in target_scene_ids:
        output_file = output_dir / f"{sid}.jsonl"
        if output_file.exists() and not allow_overwrite:
            scenes_skipped += 1
        else:
            remaining_scene_ids.append(sid)

    subagents = [
        create_scene_translator_subagent(context, allow_overwrite=allow_overwrite),
    ]

    tools = build_stats_tools(context)
    model = get_default_chat_model()
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    subagent_names = [subagent["name"] for subagent in subagents]
    logger.info("Translator coordinator starting with subagents: %s", ", ".join(subagent_names))
    logger.info("Translator progress tools: %s", ", ".join(tool_names))

    agent = create_coordinator_agent(
        model=model,
        tools=tools,
        subagents=subagents,
        system_prompt=_TRANSLATOR_SYSTEM_PROMPT,
        interrupt_on={
            "write_translation": True,
        },
        checkpointer=MemorySaver(),
    )

    if remaining_scene_ids:
        user_prompt = (
            "Translate all target scenes to the target language.\n"
            "Use task() to run the scene-translator subagent for each scene.\n"
            f"Scenes: {', '.join(remaining_scene_ids)}\n"
            "Use get_translation_progress to track progress. End when all scenes are translated."
        )

        await invoke_with_interrupts(
            cast(SupportsAinvoke, agent),
            {"messages": [{"role": "user", "content": user_prompt}]},
            decision_handler=decision_handler,
            thread_id=thread_id,
        )

    total_lines = 0
    for sid in remaining_scene_ids:
        total_lines += len(await context.load_scene_lines(sid))

    result = TranslatorResult(
        scenes_translated=len(remaining_scene_ids),
        lines_translated=total_lines,
        scenes_skipped=scenes_skipped,
    )

    logger.info("Translator pipeline complete: %s", result)
    return result


def run_translator(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[str]] | None = None,
    thread_id: str | None = None,
) -> TranslatorResult:
    """Run the Translator pipeline to translate scenes.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to translate (default: all scenes).
        allow_overwrite: Allow overwriting existing translations.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.

    Returns:
        TranslatorResult: Statistics about what was translated.
    """
    return anyio.run(
        partial(
            _run_translator_async,
            project_path,
            scene_ids=scene_ids,
            allow_overwrite=allow_overwrite,
            decision_handler=decision_handler,
            thread_id=thread_id,
        )
    )
