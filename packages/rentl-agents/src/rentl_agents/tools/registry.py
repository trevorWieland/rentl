"""Tool registry for agent tool management.

This module provides:
- ToolRegistry for storing and retrieving tools by name
- Tool resolution for agent profiles
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, PrivateAttr
from pydantic_ai import Tool

from rentl_agents.tools.game_info import GameInfoTool
from rentl_schemas.primitives import JsonValue


@runtime_checkable
class AgentToolProtocol(Protocol):
    """Protocol for agent tools.

    Tools must have a name, description, and callable execute method.
    """

    @property
    def name(self) -> str:
        """Tool identifier."""
        ...

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        ...

    def execute(self, **kwargs: JsonValue) -> dict[str, JsonValue]:
        """Execute the tool.

        Args:
            **kwargs: Tool-specific arguments.

        Returns:
            Tool result dictionary.
        """
        ...


class ToolNotFoundError(Exception):
    """Raised when a tool cannot be found in the registry.

    Attributes:
        tool_name: Name of the missing tool.
    """

    def __init__(self, message: str, tool_name: str) -> None:
        """Initialize the tool not found error.

        Args:
            message: Error message.
            tool_name: Name of the missing tool.
        """
        super().__init__(message)
        self.tool_name = tool_name


class ToolRegistry(BaseModel):
    """Registry for agent tools.

    Stores tool implementations and provides lookup by name.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    _tools: dict[str, AgentToolProtocol] = PrivateAttr(default_factory=dict)

    def register(self, tool: AgentToolProtocol) -> None:
        """Register a tool.

        Args:
            tool: Tool to register.

        Raises:
            ValueError: If tool name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} is already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool.

        Args:
            name: Tool name to unregister.
        """
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> AgentToolProtocol:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool implementation.

        Raises:
            ToolNotFoundError: If tool is not registered.
        """
        if name not in self._tools:
            available = ", ".join(sorted(self._tools.keys())) or "none"
            raise ToolNotFoundError(
                f"Tool not found: {name}. Available: {available}",
                tool_name=name,
            )
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name.

        Returns:
            True if tool is registered.
        """
        return name in self._tools

    def get_all(self) -> list[AgentToolProtocol]:
        """Get all registered tools.

        Returns:
            List of all registered tools.
        """
        return list(self._tools.values())

    def get_tools_for_agent(
        self,
        allowed_tool_names: list[str],
    ) -> list[AgentToolProtocol]:
        """Get tools allowed by an agent profile.

        Args:
            allowed_tool_names: List of tool names from agent profile.

        Returns:
            List of tool implementations.
        """
        tools: list[AgentToolProtocol] = []
        for name in allowed_tool_names:
            tools.append(self.get(name))
        return tools

    def get_tool_callables(
        self,
        allowed_tool_names: list[str],
    ) -> list[Callable[..., dict[str, JsonValue]] | Tool]:
        """Get tool execute methods for pydantic-ai registration.

        Args:
            allowed_tool_names: List of tool names from agent profile.

        Returns:
            List of tool callables or Tool wrappers.
        """
        tools = self.get_tools_for_agent(allowed_tool_names)
        return [
            Tool(
                tool.execute,
                name=tool.name,
                description=tool.description,
                takes_ctx=False,
            )
            for tool in tools
        ]


# Global default registry
_default_registry: ToolRegistry | None = None


def get_default_registry() -> ToolRegistry:
    """Get the default tool registry.

    Creates and populates it on first call.

    Returns:
        Default tool registry with standard tools registered.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
        _register_default_tools(_default_registry)
    return _default_registry


def _register_default_tools(registry: ToolRegistry) -> None:
    """Register default tools in the registry.

    Args:
        registry: Registry to populate.
    """
    # Create tool with empty context - will be replaced at runtime
    registry.register(GameInfoTool())
