"""Agent factory for instantiating phase agents."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import Field, field_validator, model_validator

from rentl_agents.harness import AgentHarness
from rentl_agents.tools import AgentTool
from rentl_core.orchestrator import PhaseAgentPool
from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_core.ports.orchestrator import (
    PhaseAgentPoolProtocol,
)
from rentl_schemas.base import BaseSchema

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT = TypeVar("OutputT", bound=BaseSchema)


class AgentConfig(BaseSchema):
    """Configuration for creating agents.

    Args:
        model_endpoint_ref: Reference to model endpoint in config.
        system_prompt: System prompt for the agent.
        user_prompt_template: User prompt template with variable substitution.
        tools: List of tool names to register.
        max_retries: Maximum retry attempts for transient failures.
        retry_base_delay: Base delay for exponential backoff in seconds.
        model_settings: Additional model settings for LLM.
    """

    model_endpoint_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to model endpoint in config",
    )
    system_prompt: str = Field(
        ...,
        min_length=1,
        description="System prompt for the agent",
    )
    user_prompt_template: str = Field(
        ...,
        min_length=1,
        description="User prompt template with variable substitution",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="List of tool names to register",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for transient failures",
    )
    retry_base_delay: float = Field(
        default=1.0,
        gt=0,
        description="Base delay for exponential backoff in seconds",
    )
    model_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional model settings for LLM",
    )

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, v: list[str]) -> list[str]:
        """Validate tool names.

        Args:
            v: List of tool names.

        Returns:
            Validated list of tool names.

        Raises:
            ValueError: If tool name is empty.
        """
        for tool_name in v:
            if not tool_name:
                raise ValueError("Tool name must not be empty")
        return v

    @model_validator(mode="after")
    def validate_config(self) -> AgentConfig:
        """Validate agent configuration.

        Returns:
            Validated agent configuration.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.system_prompt:
            raise ValueError("system_prompt must not be empty")
        if not self.user_prompt_template:
            raise ValueError("user_prompt_template must not be empty")
        return self


class AgentFactory:
    """Factory for creating agent instances and pools.

    This factory provides:
    - Agent instance creation from configuration
    - Agent pool creation for concurrent execution
    - Agent instance caching for performance
    - Tool registry management

    Usage:
        factory = AgentFactory()
        agent = factory.create_agent[InputType, OutputType](config)
        pool = factory.create_pool[InputType, OutputType](config, count=4)
    """

    def __init__(
        self,
        runtime: LlmRuntimeProtocol | None = None,
    ) -> None:
        """Initialize the agent factory.

        Args:
            runtime: Optional LLM runtime for agent execution.
        """
        self._runtime = runtime
        self._tool_registry: dict[str, Callable[[], AgentTool]] = {}
        self._instance_cache: dict[str, AgentHarness[Any, Any]] = {}

    def register_tool(
        self,
        name: str,
        tool_factory: Callable[[], AgentTool],
    ) -> None:
        """Register a tool factory.

        Args:
            name: Tool identifier.
            tool_factory: Callable that creates tool instances.

        Raises:
            ValueError: If tool name is already registered.
        """
        if name in self._tool_registry:
            raise ValueError(f"Tool {name} is already registered")
        self._tool_registry[name] = tool_factory

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool factory.

        Args:
            name: Tool identifier.
        """
        if name in self._tool_registry:
            del self._tool_registry[name]

    def create_agent[
        InputT: BaseSchema,
        OutputT: BaseSchema,
    ](
        self,
        config: AgentConfig,
        output_type: type[OutputT],
    ) -> AgentHarness[InputT, OutputT]:
        """Create an agent instance from configuration.

        Args:
            config: Agent configuration.
            output_type: Output schema type.

        Returns:
            Configured agent harness.

        Raises:
            ValueError: If configuration is invalid or runtime is not set.
        """
        if self._runtime is None:
            raise ValueError("LLM runtime must be set before creating agents")

        cache_key = self._build_cache_key(config, output_type)

        if cache_key in self._instance_cache:
            return self._instance_cache[cache_key]

        tool_list = self._build_tool_list(config.tools)

        agent = AgentHarness(
            runtime=self._runtime,
            system_prompt=config.system_prompt,
            user_prompt_template=config.user_prompt_template,
            output_type=output_type,
            tools=tool_list,
            max_retries=config.max_retries,
            retry_base_delay=config.retry_base_delay,
        )

        self._instance_cache[cache_key] = agent
        return agent

    def create_pool[
        InputT: BaseSchema,
        OutputT: BaseSchema,
    ](
        self,
        config: AgentConfig,
        output_type: type[OutputT],
        count: int,
        max_parallel: int | None = None,
    ) -> PhaseAgentPoolProtocol[InputT, OutputT]:
        """Create an agent pool from configuration.

        Args:
            config: Agent configuration.
            output_type: Output schema type.
            count: Number of agent instances to create.
            max_parallel: Optional cap on concurrent tasks.

        Returns:
            Configured agent pool.

        Raises:
            ValueError: If configuration is invalid or count is not positive.
        """
        if count <= 0:
            raise ValueError("count must be positive")

        def factory() -> AgentHarness[InputT, OutputT]:
            return self.create_agent(config, output_type)

        return PhaseAgentPool.from_factory(
            factory=factory,
            count=count,
            max_parallel=max_parallel,
        )

    def clear_cache(self) -> None:
        """Clear the agent instance cache."""
        self._instance_cache.clear()

    def _build_cache_key[
        InputT: BaseSchema,
        OutputT: BaseSchema,
    ](
        self,
        config: AgentConfig,
        output_type: type[OutputT],
    ) -> str:
        """Build a cache key for agent instance.

        Args:
            config: Agent configuration.
            output_type: Output schema type.

        Returns:
            Cache key string.
        """
        import hashlib
        import json

        config_dict = config.model_dump(mode="json")
        config_str = json.dumps(config_dict, sort_keys=True)
        type_name = output_type.__name__

        hash_obj = hashlib.sha256(config_str.encode())
        hash_hex = hash_obj.hexdigest()

        return f"{type_name}:{hash_hex[:16]}"

    def _build_tool_list(
        self,
        tool_names: list[str],
    ) -> list[dict[str, Any]]:
        """Build tool list from tool names.

        Args:
            tool_names: List of tool names.

        Returns:
            List of tool dictionaries.

        Raises:
            ValueError: If tool name is not registered.
        """
        tool_list: list[dict[str, Any]] = []

        for tool_name in tool_names:
            if tool_name not in self._tool_registry:
                raise ValueError(f"Tool {tool_name} is not registered")

            tool_factory = self._tool_registry[tool_name]
            tool = tool_factory()

            tool_list.append({
                "name": tool.name,
                "description": tool.description,
                "execute": tool.execute,
            })

        return tool_list
