"""Agent profile loader.

This module provides loading of agent profiles from TOML files with
strict validation at load time.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

from rentl_agents.templates import (
    TemplateValidationError,
    get_allowed_variables_for_layer,
    validate_template,
)
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.primitives import PhaseName

if TYPE_CHECKING:
    from rentl_schemas.base import BaseSchema


class AgentProfileLoadError(Exception):
    """Raised when agent profile loading fails.

    Attributes:
        agent_name: Name of the agent that failed to load.
        source_path: Path to the source file.
    """

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        source_path: Path | None = None,
    ) -> None:
        """Initialize the agent profile load error.

        Args:
            message: Error message.
            agent_name: Name of the agent.
            source_path: Path to the source file.
        """
        super().__init__(message)
        self.agent_name = agent_name
        self.source_path = source_path


class SchemaResolutionError(Exception):
    """Raised when output schema cannot be resolved.

    Attributes:
        schema_name: Name of the schema that couldn't be resolved.
    """

    def __init__(self, message: str, schema_name: str) -> None:
        """Initialize the schema resolution error.

        Args:
            message: Error message.
            schema_name: Name of the unresolved schema.
        """
        super().__init__(message)
        self.schema_name = schema_name


class ToolResolutionError(Exception):
    """Raised when a tool cannot be resolved.

    Attributes:
        tool_name: Name of the tool that couldn't be resolved.
    """

    def __init__(self, message: str, tool_name: str) -> None:
        """Initialize the tool resolution error.

        Args:
            message: Error message.
            tool_name: Name of the unresolved tool.
        """
        super().__init__(message)
        self.tool_name = tool_name


# Schema name to class mapping
# Add new output schemas here as they're used by agents
SCHEMA_REGISTRY: dict[str, type[BaseSchema]] = {}


def register_output_schema(name: str, schema_class: type[BaseSchema]) -> None:
    """Register an output schema for resolution.

    Args:
        name: Schema name (PascalCase, matches TOML config).
        schema_class: Pydantic schema class.

    Raises:
        ValueError: If name is already registered.
    """
    if name in SCHEMA_REGISTRY:
        raise ValueError(f"Schema {name} is already registered")
    SCHEMA_REGISTRY[name] = schema_class


def resolve_output_schema(name: str) -> type[BaseSchema]:
    """Resolve an output schema by name.

    Args:
        name: Schema name from agent profile.

    Returns:
        Pydantic schema class.

    Raises:
        SchemaResolutionError: If schema cannot be resolved.
    """
    if name not in SCHEMA_REGISTRY:
        available = ", ".join(sorted(SCHEMA_REGISTRY.keys())) or "none"
        raise SchemaResolutionError(
            f"Unknown output schema: {name}. Available: {available}",
            schema_name=name,
        )
    return SCHEMA_REGISTRY[name]


def _init_schema_registry() -> None:
    """Initialize the schema registry with known output schemas."""
    # Import here to avoid circular imports
    from rentl_schemas.phases import (
        IdiomAnnotation,
        IdiomAnnotationList,
        SceneSummary,
        TranslationResultList,
    )

    # Register all known output schemas
    if "SceneSummary" not in SCHEMA_REGISTRY:
        register_output_schema("SceneSummary", SceneSummary)
    if "IdiomAnnotation" not in SCHEMA_REGISTRY:
        register_output_schema("IdiomAnnotation", IdiomAnnotation)
    if "IdiomAnnotationList" not in SCHEMA_REGISTRY:
        register_output_schema("IdiomAnnotationList", IdiomAnnotationList)
    if "TranslationResultList" not in SCHEMA_REGISTRY:
        register_output_schema("TranslationResultList", TranslationResultList)


# Initialize on module load
_init_schema_registry()


def load_agent_profile(path: Path) -> AgentProfileConfig:
    """Load an agent profile from a TOML file.

    Performs strict validation:
    1. TOML parsing
    2. Pydantic schema validation (strict mode)
    3. Template variable validation
    4. Output schema resolution check

    Args:
        path: Path to agent TOML file.

    Returns:
        Validated agent profile configuration.

    Note:
        This is a sync convenience wrapper. For async contexts, use
        load_agent_profile_async() instead. May raise AgentProfileLoadError.
    """
    import asyncio

    # Check if there's a running event loop
    try:
        asyncio.get_running_loop()
        # If we get here, there's a running loop - use nest_asyncio pattern
        # or just run synchronously for simplicity
        return _load_agent_profile_sync(path)
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        return asyncio.run(load_agent_profile_async(path))


def _load_agent_profile_sync(path: Path) -> AgentProfileConfig:
    """Synchronously load an agent profile (internal helper).

    This is used when we're already inside an async context and can't use
    asyncio.run(). It uses blocking I/O but is safe for initialization.

    Args:
        path: Path to agent TOML file.

    Returns:
        Validated agent profile configuration.

    Raises:
        AgentProfileLoadError: If loading or validation fails.
    """
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)

        # Preprocess: convert string phase to PhaseName enum
        if "meta" in data and "phase" in data["meta"]:
            phase_str = data["meta"]["phase"]
            try:
                data["meta"]["phase"] = PhaseName(phase_str)
            except ValueError as e:
                raise AgentProfileLoadError(
                    f"Invalid phase name: {phase_str}",
                    source_path=path,
                ) from e

        profile = AgentProfileConfig.model_validate(data)

        phase_name = (
            profile.meta.phase.value
            if isinstance(profile.meta.phase, PhaseName)
            else str(profile.meta.phase)
        )
        allowed_vars = get_allowed_variables_for_layer(phase_name)

        validate_template(
            profile.prompts.agent.content,
            allowed_vars,
            context=f"{profile.meta.name} agent system prompt",
        )

        validate_template(
            profile.prompts.user_template.content,
            allowed_vars,
            context=f"{profile.meta.name} user prompt template",
        )

        resolve_output_schema(profile.meta.output_schema)
        return profile

    except FileNotFoundError as e:
        raise AgentProfileLoadError(
            f"Agent profile file not found: {path}",
            source_path=path,
        ) from e
    except tomllib.TOMLDecodeError as e:
        raise AgentProfileLoadError(
            f"Invalid TOML in agent profile: {e}",
            source_path=path,
        ) from e
    except TemplateValidationError as e:
        raise AgentProfileLoadError(
            str(e),
            source_path=path,
        ) from e
    except SchemaResolutionError as e:
        raise AgentProfileLoadError(
            str(e),
            source_path=path,
        ) from e
    except Exception as e:
        raise AgentProfileLoadError(
            f"Failed to load agent profile: {e}",
            source_path=path,
        ) from e


async def load_agent_profile_async(path: Path) -> AgentProfileConfig:
    """Load an agent profile from a TOML file asynchronously.

    Performs strict validation:
    1. TOML parsing
    2. Pydantic schema validation (strict mode)
    3. Template variable validation
    4. Output schema resolution check

    Args:
        path: Path to agent TOML file.

    Returns:
        Validated agent profile configuration.

    Raises:
        AgentProfileLoadError: If loading or validation fails.
    """
    try:
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()
            data = tomllib.loads(content.decode("utf-8"))

        # Preprocess: convert string phase to PhaseName enum
        # This is needed because BaseSchema uses strict=True
        if "meta" in data and "phase" in data["meta"]:
            phase_str = data["meta"]["phase"]
            try:
                data["meta"]["phase"] = PhaseName(phase_str)
            except ValueError as e:
                raise AgentProfileLoadError(
                    f"Invalid phase name: {phase_str}",
                    source_path=path,
                ) from e

        # Parse and validate against schema
        profile = AgentProfileConfig.model_validate(data)

        # Validate template variables in prompts
        # Note: with use_enum_values=True, phase is stored as string
        phase_name = (
            profile.meta.phase.value
            if isinstance(profile.meta.phase, PhaseName)
            else str(profile.meta.phase)
        )
        allowed_vars = get_allowed_variables_for_layer(phase_name)

        validate_template(
            profile.prompts.agent.content,
            allowed_vars,
            context=f"{profile.meta.name} agent system prompt",
        )

        validate_template(
            profile.prompts.user_template.content,
            allowed_vars,
            context=f"{profile.meta.name} user prompt template",
        )

        # Verify output schema can be resolved
        resolve_output_schema(profile.meta.output_schema)

        return profile

    except FileNotFoundError as e:
        raise AgentProfileLoadError(
            f"Agent profile file not found: {path}",
            source_path=path,
        ) from e
    except tomllib.TOMLDecodeError as e:
        raise AgentProfileLoadError(
            f"Invalid TOML in agent profile: {e}",
            source_path=path,
        ) from e
    except TemplateValidationError as e:
        raise AgentProfileLoadError(
            str(e),
            source_path=path,
        ) from e
    except SchemaResolutionError as e:
        raise AgentProfileLoadError(
            str(e),
            source_path=path,
        ) from e
    except Exception as e:
        raise AgentProfileLoadError(
            f"Failed to load agent profile: {e}",
            source_path=path,
        ) from e


def discover_agent_profiles(agents_dir: Path) -> dict[str, AgentProfileConfig]:
    """Discover and load all agent profiles from a directory.

    Expected structure:
        agents_dir/
        ├── context/
        │   └── scene_summarizer.toml
        ├── pretranslation/
        │   └── ...
        └── translate/
            └── ...

    Args:
        agents_dir: Base directory containing phase subdirectories.

    Returns:
        Dictionary mapping agent names to profiles.

    Raises:
        AgentProfileLoadError: If any profile fails to load.
    """
    profiles: dict[str, AgentProfileConfig] = {}

    if not agents_dir.exists():
        return profiles

    # Scan phase directories
    for phase in PhaseName:
        # Skip ingest and export - they don't use agents
        if phase in {PhaseName.INGEST, PhaseName.EXPORT}:
            continue

        phase_dir = agents_dir / phase.value
        if not phase_dir.exists():
            continue

        # Load all TOML files in phase directory
        for toml_path in phase_dir.glob("*.toml"):
            profile = load_agent_profile(toml_path)

            # Verify phase matches directory
            if profile.meta.phase != phase:
                phase_declared = profile.meta.phase.value
                raise AgentProfileLoadError(
                    f"Agent {profile.meta.name} declares phase {phase_declared} "
                    f"but is in {phase.value}/ directory",
                    agent_name=profile.meta.name,
                    source_path=toml_path,
                )

            profiles[profile.meta.name] = profile

    return profiles


def get_agents_for_phase(
    profiles: dict[str, AgentProfileConfig],
    phase: PhaseName,
) -> list[AgentProfileConfig]:
    """Get all agents for a specific phase, sorted by priority.

    Args:
        profiles: All loaded agent profiles.
        phase: Phase to filter by.

    Returns:
        List of agent profiles sorted by priority (lower = first).
    """
    phase_agents = [p for p in profiles.values() if p.meta.phase == phase]
    return sorted(phase_agents, key=lambda p: p.orchestration.priority)
