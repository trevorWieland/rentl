"""Agent factory for instantiating phase agents."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeGuard

from pydantic import Field, field_validator, model_validator

from rentl_agents.harness import AgentHarness
from rentl_agents.tools import AgentTool
from rentl_core.orchestrator import PhaseAgentPool
from rentl_core.ports.orchestrator import (
    PhaseAgentPoolProtocol,
)
from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import JsonValue


class AgentConfig(BaseSchema):
    """Configuration for creating agents.

    Args:
        model_endpoint_ref: Reference to model endpoint in config.
        system_prompt: System prompt for the agent.
        user_prompt_template: User prompt template with variable substitution.
        tools: List of tool names to register.
        max_retries: Maximum retry attempts for transient failures.
        retry_base_delay: Base delay for exponential backoff in seconds.
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


@dataclass
class _AgentCacheEntry[OutputT: BaseSchema]:
    """Type-erased cache entry for agent instances.

    Stores the agent harness with runtime type information for safe retrieval.
    """

    agent: AgentHarness[BaseSchema, OutputT]
    output_type: type[OutputT]


def _entry_matches_output_type[OutputT: BaseSchema](
    entry: _AgentCacheEntry[BaseSchema],
    output_type: type[OutputT],
) -> TypeGuard[_AgentCacheEntry[OutputT]]:
    return entry.output_type is output_type


class AgentFactory:
    """Factory for creating and caching agent instances.

    This factory manages agent lifecycle and provides caching for
    performance optimization.
    """

    def __init__(
        self, tool_registry: dict[str, Callable[[], AgentTool]] | None = None
    ) -> None:
        """Initialize the factory with a tool registry.

        Args:
            tool_registry: Dictionary mapping tool names to tool factories.
                Defaults to empty dict if not provided.
        """
        self._tool_registry = tool_registry if tool_registry is not None else {}
        self._instance_cache: dict[str, _AgentCacheEntry[BaseSchema]] = {}

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
        OutputT: BaseSchema,
    ](
        self,
        config: AgentConfig,
        output_type: type[OutputT],
    ) -> AgentHarness[BaseSchema, OutputT]:
        """Create an agent instance from configuration.

        Args:
            config: Agent configuration.
            output_type: Output schema type.

        Returns:
            Configured agent harness.
        """
        cache_key = self._build_cache_key(config, output_type)

        cached = self._instance_cache.get(cache_key)
        if cached is not None and _entry_matches_output_type(cached, output_type):
            return cached.agent

        tool_callables = self._build_tool_list(config.tools)

        agent: AgentHarness[BaseSchema, OutputT] = AgentHarness(
            system_prompt=config.system_prompt,
            user_prompt_template=config.user_prompt_template,
            output_type=output_type,
            tools=tool_callables,
            max_retries=config.max_retries,
            retry_base_delay=config.retry_base_delay,
        )

        self._instance_cache[cache_key] = _AgentCacheEntry[BaseSchema](
            agent=agent,
            output_type=output_type,
        )
        return agent

    def create_pool[
        OutputT: BaseSchema,
    ](
        self,
        config: AgentConfig,
        output_type: type[OutputT],
        count: int,
        max_parallel: int | None = None,
    ) -> PhaseAgentPoolProtocol[BaseSchema, OutputT]:
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

        def factory() -> AgentHarness[BaseSchema, OutputT]:
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
        config_dict = config.model_dump(mode="json")
        config_str = json.dumps(config_dict, sort_keys=True)
        type_name = output_type.__name__

        hash_obj = hashlib.sha256(config_str.encode())
        hash_hex = hash_obj.hexdigest()

        return f"{type_name}:{hash_hex[:16]}"

    def _build_tool_list(
        self,
        tool_names: list[str],
    ) -> list[Callable[..., dict[str, JsonValue]]]:
        """Build tool list from tool names.

        Args:
            tool_names: List of tool names.

        Returns:
            List of tool callables.

        Raises:
            ValueError: If tool name is not registered.
        """
        tool_list: list[Callable[..., dict[str, JsonValue]]] = []

        for tool_name in tool_names:
            if tool_name not in self._tool_registry:
                raise ValueError(f"Tool {tool_name} is not registered")

            tool_factory = self._tool_registry[tool_name]
            tool = tool_factory()

            tool_list.append(tool.execute)

        return tool_list
