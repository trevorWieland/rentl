"""Agent profile configuration schemas.

This module defines the schema for fully declarative agent profiles loaded from TOML.
Agents are defined as configuration, not code, enabling:
- Community contribution via TOML files
- Easy prompt tuning and A/B testing
- Version tracking for reproducibility
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import PhaseName


class AgentProfileMeta(BaseSchema):
    """Agent profile metadata.

    Identifies the agent and its role in the pipeline.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Agent identifier (snake_case)",
    )
    version: str = Field(
        ...,
        min_length=5,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version (e.g., 1.0.0)",
    )
    phase: PhaseName = Field(..., description="Pipeline phase this agent belongs to")
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable agent description",
    )
    output_schema: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z][a-zA-Z0-9]*$",
        description="Output schema name (PascalCase, references rentl_schemas)",
    )


class AgentRequirements(BaseSchema):
    """Agent validation requirements.

    Defines preconditions that must be met for the agent to execute.
    """

    scene_id_required: bool = Field(
        False,
        description="Require scene_id on all source lines",
    )


class AgentOrchestration(BaseSchema):
    """Agent orchestration configuration for multi-agent phases (v0.2+).

    Controls execution order when multiple agents run in the same phase.
    """

    priority: int = Field(
        10,
        ge=1,
        le=100,
        description="Execution priority (lower = earlier, 1-100)",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Agent names that must complete before this agent runs",
    )

    @field_validator("depends_on")
    @classmethod
    def validate_depends_on(cls, v: list[str]) -> list[str]:
        """Validate dependency agent names.

        Args:
            v: List of agent names.

        Returns:
            Validated list of agent names.

        Raises:
            ValueError: If agent name is empty or invalid format.
        """
        for name in v:
            if not name:
                raise ValueError("Dependency agent name must not be empty")
            if not name.replace("_", "").isalnum():
                raise ValueError(f"Invalid agent name format: {name}")
        return v


class AgentPromptContent(BaseSchema):
    """Single prompt content block."""

    content: str = Field(
        ...,
        min_length=1,
        description="Prompt content with optional {{variable}} placeholders",
    )


class AgentPromptConfig(BaseSchema):
    """Agent prompt configuration.

    Contains the agent-specific prompts that are combined with root and phase layers.
    """

    agent: AgentPromptContent = Field(
        ..., description="Agent-layer system prompt content"
    )
    user_template: AgentPromptContent = Field(
        ..., description="User prompt template with {{variable}} placeholders"
    )


class ToolAccessConfig(BaseSchema):
    """Tool access configuration.

    Defines which tools the agent can use during execution.
    """

    allowed: list[str] = Field(
        default_factory=list,
        description="List of allowed tool names",
    )
    required: list[str] = Field(
        default_factory=list,
        description="List of tools that must be called before output",
    )

    @field_validator("allowed", "required")
    @classmethod
    def validate_allowed_tools(cls, v: list[str]) -> list[str]:
        """Validate tool names.

        Args:
            v: List of tool names.

        Returns:
            Validated list of tool names.

        Raises:
            ValueError: If tool name is empty or invalid format.
        """
        for name in v:
            if not name:
                raise ValueError("Tool name must not be empty")
            if not name.replace("_", "").isalnum():
                raise ValueError(f"Invalid tool name format: {name}")
        return v

    @model_validator(mode="after")
    def validate_required_subset(self) -> ToolAccessConfig:
        """Validate required tools are a subset of allowed tools.

        Returns:
            ToolAccessConfig: Validated tool access config.

        Raises:
            ValueError: If required tools are not included in allowed tools.
        """
        required_set = set(self.required)
        allowed_set = set(self.allowed)
        if not required_set.issubset(allowed_set):
            missing = sorted(required_set.difference(allowed_set))
            joined = ", ".join(missing)
            raise ValueError(f"required tools must be in allowed tools: {joined}")
        return self


class ModelHints(BaseSchema):
    """Model recommendations and requirements.

    Provider-agnostic hints for model selection. Model IDs are opaque strings
    that match whatever the user has configured in their endpoint.
    """

    recommended: list[str] = Field(
        default_factory=list,
        description="Recommended model IDs (provider-agnostic)",
    )
    min_context_tokens: int | None = Field(
        None,
        ge=1024,
        description="Minimum context window size in tokens",
    )
    benefits_from_reasoning: bool = Field(
        False,
        description="Whether this agent benefits from extended thinking/reasoning",
    )


class AgentProfileConfig(BaseSchema):
    """Full agent profile configuration.

    Complete definition of an agent loaded from TOML. Validated strictly at load time
    to catch configuration errors before pipeline execution.
    """

    meta: AgentProfileMeta = Field(..., description="Agent metadata")
    requirements: AgentRequirements = Field(
        default_factory=AgentRequirements,
        description="Agent validation requirements",
    )
    orchestration: AgentOrchestration = Field(
        default_factory=AgentOrchestration,
        description="Multi-agent orchestration settings",
    )
    prompts: AgentPromptConfig = Field(..., description="Agent prompts")
    tools: ToolAccessConfig = Field(
        default_factory=ToolAccessConfig,
        description="Tool access configuration",
    )
    model_hints: ModelHints = Field(
        default_factory=ModelHints,
        description="Model recommendations and requirements",
    )

    @model_validator(mode="after")
    def validate_profile(self) -> AgentProfileConfig:
        """Validate agent profile consistency.

        Returns:
            Validated agent profile.

        Raises:
            ValueError: If profile is invalid.
        """
        # Ensure agent doesn't depend on itself
        if self.meta.name in self.orchestration.depends_on:
            raise ValueError(f"Agent {self.meta.name} cannot depend on itself")
        return self


class PromptLayerContent(BaseSchema):
    """Content for a prompt layer (root or phase)."""

    content: str = Field(
        ...,
        min_length=1,
        description="Prompt layer content with {{variable}} placeholders",
    )


class PhasePromptConfig(BaseSchema):
    """Phase-level prompt configuration."""

    phase: PhaseName = Field(..., description="Phase this config applies to")
    output_language: str = Field(
        "source",
        pattern=r"^(source|target)$",
        description="Output language mode: 'source' or 'target'",
    )
    system: PromptLayerContent = Field(..., description="Phase-layer system prompt")


class RootPromptConfig(BaseSchema):
    """Root-level prompt configuration."""

    system: PromptLayerContent = Field(..., description="Root-layer system prompt")
