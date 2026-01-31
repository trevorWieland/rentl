"""Profile agent factory for creating orchestrator-ready agents.

This module provides factory functions to create phase agents from TOML profiles
and wire them to the pipeline orchestrator.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rentl_agents.context.scene import (
    format_scene_lines,
    group_lines_by_scene,
)
from rentl_agents.layers import load_layer_registry
from rentl_agents.profiles.loader import load_agent_profile
from rentl_agents.runtime import ProfileAgent, ProfileAgentConfig
from rentl_agents.templates import TemplateContext
from rentl_agents.tools.registry import ToolRegistry, get_default_registry
from rentl_schemas.phases import (
    ContextPhaseInput,
    ContextPhaseOutput,
    SceneSummary,
)
from rentl_schemas.primitives import PhaseName

if TYPE_CHECKING:
    pass


class ContextSceneSummarizerAgent:
    """Context phase agent that summarizes scenes using a ProfileAgent.

    This agent:
    1. Validates that all lines have scene_id (required by SceneSummarizer)
    2. Groups lines by scene
    3. Runs ProfileAgent for each scene to produce SceneSummary
    4. Merges results into ContextPhaseOutput
    """

    def __init__(
        self,
        profile_agent: ProfileAgent[ContextPhaseInput, SceneSummary],
        config: ProfileAgentConfig,
    ) -> None:
        """Initialize the context scene summarizer agent.

        Args:
            profile_agent: Underlying ProfileAgent for scene summarization.
            config: Runtime configuration.
        """
        self._profile_agent = profile_agent
        self._config = config

    async def run(self, payload: ContextPhaseInput) -> ContextPhaseOutput:
        """Execute context phase by summarizing each scene.

        Args:
            payload: Context phase input with source lines.

        Returns:
            Context phase output with scene summaries.
        """
        from rentl_agents.context.scene import validate_scene_input

        # Validate all lines have scene_id
        validate_scene_input(payload.source_lines)

        # Group lines by scene
        scene_groups = group_lines_by_scene(payload.source_lines)

        # Summarize each scene
        summaries: list[SceneSummary] = []
        for scene_id, lines in scene_groups.items():
            # Update template context for this scene
            scene_lines_text = format_scene_lines(lines)
            context = TemplateContext(
                root_variables={},
                phase_variables={},
                agent_variables={
                    "scene_id": scene_id,
                    "line_count": str(len(lines)),
                    "scene_lines": scene_lines_text,
                },
            )
            self._profile_agent.update_context(context)

            # Run the profile agent for this scene
            # Note: ProfileAgent returns SceneSummary directly
            summary = await self._profile_agent.run(payload)
            summaries.append(summary)

        return ContextPhaseOutput(
            run_id=payload.run_id,
            scene_summaries=summaries,
            context_notes=[],
            project_context=payload.project_context,
            style_guide=payload.style_guide,
            glossary=payload.glossary,
        )


def create_context_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
) -> ContextSceneSummarizerAgent:
    """Create a context phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.

    Returns:
        Context phase agent ready for orchestrator.

    Raises:
        ValueError: If profile is not for context phase.
    """
    # Load the profile
    profile = load_agent_profile(profile_path)

    # Verify it's a context phase agent
    if profile.meta.phase != PhaseName.CONTEXT:
        raise ValueError(
            f"Profile {profile.meta.name} is for phase {profile.meta.phase.value}, "
            f"expected context"
        )

    # Load prompt layers
    layer_registry = load_layer_registry(prompts_dir)

    # Get tool registry
    if tool_registry is None:
        tool_registry = get_default_registry()

    # Create the ProfileAgent
    profile_agent: ProfileAgent[ContextPhaseInput, SceneSummary] = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=layer_registry,
        tool_registry=tool_registry,
        config=config,
    )

    # Wrap in ContextSceneSummarizerAgent
    return ContextSceneSummarizerAgent(
        profile_agent=profile_agent,
        config=config,
    )


def get_default_prompts_dir() -> Path:
    """Get the default prompts directory path.

    Returns:
        Path to the prompts directory in rentl-agents package.
    """
    # Navigate from this file to the package prompts directory
    # File is in: packages/rentl-agents/src/rentl_agents/wiring.py
    # Prompts are in: packages/rentl-agents/prompts/
    package_root = Path(__file__).parent.parent.parent  # Up to rentl-agents/
    return package_root / "prompts"


def get_default_agents_dir() -> Path:
    """Get the default agents directory path.

    Returns:
        Path to the agents directory in rentl-agents package.
    """
    # Navigate from this file to the package agents directory
    # File is in: packages/rentl-agents/src/rentl_agents/wiring.py
    # Agents are in: packages/rentl-agents/agents/
    package_root = Path(__file__).parent.parent.parent  # Up to rentl-agents/
    return package_root / "agents"
