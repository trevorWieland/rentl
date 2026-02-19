"""Prompt layer system for three-tier prompt composition.

This module provides:
- PromptLayerRegistry for storing root and phase layer prompts
- PromptComposer for combining layers into final system prompts
- Layer loading from TOML files
"""

from __future__ import annotations

import asyncio
import tomllib
from pathlib import Path

import aiofiles
from pydantic import BaseModel, Field

from rentl_agents.templates import (
    TemplateContext,
    TemplateValidationError,
    get_allowed_variables_for_layer,
    validate_template,
)
from rentl_schemas.agents import (
    AgentProfileConfig,
    PhasePromptConfig,
    RootPromptConfig,
)
from rentl_schemas.primitives import PhaseName


class LayerLoadError(Exception):
    """Raised when a prompt layer fails to load.

    Attributes:
        layer_name: Name of the layer that failed.
        source_path: Path to the source file.
    """

    def __init__(
        self,
        message: str,
        layer_name: str,
        source_path: Path | None = None,
    ) -> None:
        """Initialize the layer load error.

        Args:
            message: Error message.
            layer_name: Name of the layer.
            source_path: Path to the source file.
        """
        super().__init__(message)
        self.layer_name = layer_name
        self.source_path = source_path


class PromptLayerRegistry(BaseModel):
    """Registry for prompt layer configurations.

    Stores root and phase layer prompts for composition.
    """

    root: RootPromptConfig | None = Field(
        default=None, description="Root layer prompt configuration"
    )
    phases: dict[PhaseName, PhasePromptConfig] = Field(
        default_factory=dict,
        description="Phase layer prompt configurations keyed by phase name",
    )

    def set_root(self, config: RootPromptConfig) -> None:
        """Set the root layer configuration.

        Args:
            config: Root prompt configuration.
        """
        self.root = config

    def set_phase(self, config: PhasePromptConfig) -> None:
        """Set a phase layer configuration.

        Args:
            config: Phase prompt configuration.
        """
        self.phases[config.phase] = config

    def get_phase(self, phase: PhaseName) -> PhasePromptConfig | None:
        """Get a phase layer configuration.

        Args:
            phase: Phase name.

        Returns:
            Phase configuration or None if not set.
        """
        return self.phases.get(phase)

    def has_root(self) -> bool:
        """Check if root layer is configured.

        Returns:
            True if root layer is set.
        """
        return self.root is not None

    def has_phase(self, phase: PhaseName) -> bool:
        """Check if a phase layer is configured.

        Args:
            phase: Phase name.

        Returns:
            True if phase layer is set.
        """
        return phase in self.phases


def load_root_prompt(path: Path) -> RootPromptConfig:
    """Load root prompt configuration from TOML file.

    Args:
        path: Path to root.toml file.

    Returns:
        Validated root prompt configuration.

    Note:
        This is a sync convenience wrapper. For async contexts, use
        load_root_prompt_async() instead. May raise LayerLoadError.
    """
    try:
        asyncio.get_running_loop()
        return load_root_prompt_sync(path)
    except RuntimeError:
        return asyncio.run(load_root_prompt_async(path))


def load_root_prompt_sync(path: Path) -> RootPromptConfig:
    """Load root prompt configuration synchronously.

    Args:
        path: Path to root.toml file.

    Returns:
        Validated root prompt configuration.
    """
    return _load_root_prompt_sync(path)


def _load_root_prompt_sync(path: Path) -> RootPromptConfig:
    """Synchronously load root prompt (internal helper).

    Args:
        path: Path to root.toml file.

    Returns:
        Validated root prompt configuration.

    Raises:
        LayerLoadError: If loading or validation fails.
    """
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)

        config = RootPromptConfig.model_validate(data)

        validate_template(
            config.system.content,
            get_allowed_variables_for_layer("root"),
            context="root layer system prompt",
        )

        return config

    except FileNotFoundError as e:
        raise LayerLoadError(
            f"Root prompt file not found: {path}",
            layer_name="root",
            source_path=path,
        ) from e
    except tomllib.TOMLDecodeError as e:
        raise LayerLoadError(
            f"Invalid TOML in root prompt: {e}",
            layer_name="root",
            source_path=path,
        ) from e
    except TemplateValidationError as e:
        raise LayerLoadError(
            str(e),
            layer_name="root",
            source_path=path,
        ) from e
    except Exception as e:
        raise LayerLoadError(
            f"Failed to load root prompt: {e}",
            layer_name="root",
            source_path=path,
        ) from e


async def load_root_prompt_async(path: Path) -> RootPromptConfig:
    """Load root prompt configuration from TOML file asynchronously.

    Args:
        path: Path to root.toml file.

    Returns:
        Validated root prompt configuration.

    Raises:
        LayerLoadError: If loading or validation fails.
    """
    try:
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()
            data = tomllib.loads(content.decode("utf-8"))

        config = RootPromptConfig.model_validate(data)

        # Validate template variables
        validate_template(
            config.system.content,
            get_allowed_variables_for_layer("root"),
            context="root layer system prompt",
        )

        return config

    except FileNotFoundError as e:
        raise LayerLoadError(
            f"Root prompt file not found: {path}",
            layer_name="root",
            source_path=path,
        ) from e
    except tomllib.TOMLDecodeError as e:
        raise LayerLoadError(
            f"Invalid TOML in root prompt: {e}",
            layer_name="root",
            source_path=path,
        ) from e
    except TemplateValidationError as e:
        raise LayerLoadError(
            str(e),
            layer_name="root",
            source_path=path,
        ) from e
    except Exception as e:
        raise LayerLoadError(
            f"Failed to load root prompt: {e}",
            layer_name="root",
            source_path=path,
        ) from e


def load_phase_prompt(path: Path) -> PhasePromptConfig:
    """Load phase prompt configuration from TOML file.

    Args:
        path: Path to phase TOML file.

    Returns:
        Validated phase prompt configuration.

    Note:
        This is a sync convenience wrapper. For async contexts, use
        load_phase_prompt_async() instead. May raise LayerLoadError.
    """
    try:
        asyncio.get_running_loop()
        return load_phase_prompt_sync(path)
    except RuntimeError:
        return asyncio.run(load_phase_prompt_async(path))


def load_phase_prompt_sync(path: Path) -> PhasePromptConfig:
    """Load phase prompt configuration synchronously.

    Args:
        path: Path to phase TOML file.

    Returns:
        Validated phase prompt configuration.
    """
    return _load_phase_prompt_sync(path)


def _load_phase_prompt_sync(path: Path) -> PhasePromptConfig:
    """Synchronously load phase prompt (internal helper).

    Args:
        path: Path to phase TOML file.

    Returns:
        Validated phase prompt configuration.

    Raises:
        LayerLoadError: If loading or validation fails.
    """
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)

        if "meta" in data and "phase" in data["meta"]:
            phase_name = data["meta"]["phase"]
            data["phase"] = phase_name
            del data["meta"]

        if "phase" in data and isinstance(data["phase"], str):
            data["phase"] = PhaseName(data["phase"])

        config = PhasePromptConfig.model_validate(data)

        phase_value = (
            config.phase.value
            if isinstance(config.phase, PhaseName)
            else str(config.phase)
        )
        validate_template(
            config.system.content,
            get_allowed_variables_for_layer("phase"),
            context=f"{phase_value} phase layer system prompt",
        )

        return config

    except FileNotFoundError as e:
        raise LayerLoadError(
            f"Phase prompt file not found: {path}",
            layer_name="phase",
            source_path=path,
        ) from e
    except tomllib.TOMLDecodeError as e:
        raise LayerLoadError(
            f"Invalid TOML in phase prompt: {e}",
            layer_name="phase",
            source_path=path,
        ) from e
    except TemplateValidationError as e:
        raise LayerLoadError(
            str(e),
            layer_name="phase",
            source_path=path,
        ) from e
    except Exception as e:
        raise LayerLoadError(
            f"Failed to load phase prompt: {e}",
            layer_name="phase",
            source_path=path,
        ) from e


async def load_phase_prompt_async(path: Path) -> PhasePromptConfig:
    """Load phase prompt configuration from TOML file asynchronously.

    Args:
        path: Path to phase TOML file.

    Returns:
        Validated phase prompt configuration.

    Raises:
        LayerLoadError: If loading or validation fails.
    """
    try:
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()
            data = tomllib.loads(content.decode("utf-8"))

        # Handle both nested 'meta.phase' and flat 'phase' formats
        if "meta" in data and "phase" in data["meta"]:
            phase_name = data["meta"]["phase"]
            # Flatten for validation
            data["phase"] = phase_name
            del data["meta"]

        # Convert string phase to PhaseName enum (needed for strict mode)
        if "phase" in data and isinstance(data["phase"], str):
            data["phase"] = PhaseName(data["phase"])

        config = PhasePromptConfig.model_validate(data)

        # Validate template variables
        phase_value = (
            config.phase.value
            if isinstance(config.phase, PhaseName)
            else str(config.phase)
        )
        validate_template(
            config.system.content,
            get_allowed_variables_for_layer("phase"),
            context=f"{phase_value} phase layer system prompt",
        )

        return config

    except FileNotFoundError as e:
        raise LayerLoadError(
            f"Phase prompt file not found: {path}",
            layer_name="phase",
            source_path=path,
        ) from e
    except tomllib.TOMLDecodeError as e:
        raise LayerLoadError(
            f"Invalid TOML in phase prompt: {e}",
            layer_name="phase",
            source_path=path,
        ) from e
    except TemplateValidationError as e:
        raise LayerLoadError(
            str(e),
            layer_name="phase",
            source_path=path,
        ) from e
    except Exception as e:
        raise LayerLoadError(
            f"Failed to load phase prompt: {e}",
            layer_name="phase",
            source_path=path,
        ) from e


def load_layer_registry(prompts_dir: Path) -> PromptLayerRegistry:
    """Load all prompt layers from a directory.

    Expected structure:
        prompts_dir/
        ├── root.toml
        └── phases/
            ├── context.toml
            ├── pretranslation.toml
            ├── translate.toml
            ├── qa.toml
            └── edit.toml

    Args:
        prompts_dir: Base directory containing prompt files.

    Returns:
        Populated prompt layer registry.
    """
    registry = PromptLayerRegistry()

    # Load root layer
    root_path = prompts_dir / "root.toml"
    if root_path.exists():
        registry.set_root(load_root_prompt(root_path))

    # Load phase layers
    phases_dir = prompts_dir / "phases"
    if phases_dir.exists():
        for phase in PhaseName:
            # Skip ingest and export - they don't use agents
            if phase in {PhaseName.INGEST, PhaseName.EXPORT}:
                continue

            phase_path = phases_dir / f"{phase.value}.toml"
            if phase_path.exists():
                registry.set_phase(load_phase_prompt(phase_path))

    return registry


class PromptComposer(BaseModel):
    """Composes final prompts from three layers.

    Combines root, phase, and agent layer prompts into the final
    system prompt used for LLM calls.
    """

    registry: PromptLayerRegistry = Field(
        description="Prompt layer registry with root and phase configurations"
    )
    separator: str = Field(
        default="\n\n---\n\n", description="Separator inserted between prompt layers"
    )

    def compose_system_prompt(
        self,
        agent_profile: AgentProfileConfig,
        context: TemplateContext,
    ) -> str:
        """Compose the final system prompt from all layers.

        Args:
            agent_profile: Agent profile with agent-layer prompt.
            context: Template context with variables for rendering.

        Returns:
            Composed system prompt with all layers.
        """
        parts: list[str] = []

        # Root layer
        if self.registry.root is not None:
            root_prompt = context.render(
                self.registry.root.system.content,
                strict=False,  # Allow missing vars at composition time
            )
            if root_prompt.strip():
                parts.append(root_prompt.strip())

        # Phase layer
        phase_config = self.registry.get_phase(agent_profile.meta.phase)
        if phase_config is not None:
            phase_prompt = context.render(
                phase_config.system.content,
                strict=False,
            )
            if phase_prompt.strip():
                parts.append(phase_prompt.strip())

        # Agent layer
        agent_prompt = context.render(
            agent_profile.prompts.agent.content,
            strict=False,
        )
        if agent_prompt.strip():
            parts.append(agent_prompt.strip())

        return self.separator.join(parts)

    def render_user_prompt(
        self,
        agent_profile: AgentProfileConfig,
        context: TemplateContext,
    ) -> str:
        """Render the user prompt template.

        Args:
            agent_profile: Agent profile with user prompt template.
            context: Template context with variables for rendering.

        Returns:
            Rendered user prompt.
        """
        return context.render(
            agent_profile.prompts.user_template.content,
            strict=True,  # User prompt should have all variables
        )
