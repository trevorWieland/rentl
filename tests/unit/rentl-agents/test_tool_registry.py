"""Unit tests for tool registry."""

from __future__ import annotations

import pytest
from pydantic_ai import Tool

from rentl_agents.tools import (
    GameInfoTool,
    ProjectContext,
    ToolNotFoundError,
    ToolRegistry,
    get_default_registry,
)


class TestToolRegistry:
    """Test cases for ToolRegistry class."""

    def test_create_empty_registry(self) -> None:
        """Test creating empty registry."""
        registry = ToolRegistry()

        assert registry.get_all() == []

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = GameInfoTool()

        registry.register(tool)

        assert registry.has("get_game_info")
        assert registry.get("get_game_info") == tool

    def test_register_duplicate_raises(self) -> None:
        """Test registering duplicate tool raises error."""
        registry = ToolRegistry()
        tool1 = GameInfoTool()
        tool2 = GameInfoTool()

        registry.register(tool1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)

    def test_unregister_tool(self) -> None:
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = GameInfoTool()

        registry.register(tool)
        registry.unregister("get_game_info")

        assert not registry.has("get_game_info")

    def test_unregister_nonexistent_is_safe(self) -> None:
        """Test unregistering nonexistent tool is safe."""
        registry = ToolRegistry()

        # Should not raise
        registry.unregister("nonexistent")

    def test_get_missing_tool_raises(self) -> None:
        """Test getting missing tool raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError) as exc_info:
            registry.get("nonexistent")

        assert exc_info.value.tool_name == "nonexistent"

    def test_get_all_tools(self) -> None:
        """Test getting all registered tools."""
        registry = ToolRegistry()
        tool = GameInfoTool()

        registry.register(tool)

        all_tools = registry.get_all()
        assert len(all_tools) == 1
        assert all_tools[0] == tool

    def test_get_tools_for_agent(self) -> None:
        """Test getting tools for agent profile."""
        registry = ToolRegistry()
        tool = GameInfoTool()
        registry.register(tool)

        tools = registry.get_tools_for_agent(["get_game_info"])

        assert len(tools) == 1
        assert tools[0] == tool

    def test_get_tools_for_agent_missing_raises(self) -> None:
        """Test getting missing tool for agent raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError):
            registry.get_tools_for_agent(["nonexistent"])

    def test_get_tool_callables(self) -> None:
        """Test getting tool callables."""
        registry = ToolRegistry()
        tool = GameInfoTool()
        registry.register(tool)

        callables = registry.get_tool_callables(["get_game_info"])

        assert len(callables) == 1
        assert isinstance(callables[0], Tool)
        assert callables[0].name == "get_game_info"


class TestGameInfoTool:
    """Test cases for GameInfoTool class."""

    def test_tool_properties(self) -> None:
        """Test tool name and description."""
        tool = GameInfoTool()

        assert tool.name == "get_game_info"
        assert "game" in tool.description.lower()

    def test_execute_default_context(self) -> None:
        """Test executing with default context."""
        tool = GameInfoTool()

        result = tool.execute()

        assert "game_name" in result
        assert result["game_name"] == "Unknown Game"

    def test_execute_with_context(self) -> None:
        """Test executing with custom context."""
        context = ProjectContext(
            game_name="Test Game",
            synopsis="A test game",
            source_language="ja",
            target_languages=["en", "de"],
        )
        tool = GameInfoTool(context=context)

        result = tool.execute()

        assert result["game_name"] == "Test Game"
        assert result["synopsis"] == "A test game"
        assert result["source_language"] == "ja"
        assert result["target_languages"] == ["en", "de"]

    def test_update_context(self) -> None:
        """Test updating tool context."""
        tool = GameInfoTool()
        new_context = ProjectContext(game_name="Updated Game")

        tool.update_context(new_context)
        result = tool.execute()

        assert result["game_name"] == "Updated Game"


class TestGetDefaultRegistry:
    """Test cases for get_default_registry function."""

    def test_returns_registry(self) -> None:
        """Test default registry is returned."""
        registry = get_default_registry()

        assert isinstance(registry, ToolRegistry)

    def test_has_game_info_tool(self) -> None:
        """Test default registry has game info tool."""
        registry = get_default_registry()

        assert registry.has("get_game_info")

    def test_returns_same_instance(self) -> None:
        """Test returns same registry instance."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()

        assert registry1 is registry2


class TestProjectContext:
    """Test cases for ProjectContext dataclass."""

    def test_default_values(self) -> None:
        """Test default context values."""
        context = ProjectContext()

        assert context.game_name == "Unknown Game"
        assert context.synopsis is None
        assert context.source_language == "ja"
        assert context.target_languages == []

    def test_custom_values(self) -> None:
        """Test custom context values."""
        context = ProjectContext(
            game_name="My Game",
            synopsis="An adventure game",
            source_language="en",
            target_languages=["ja", "ko"],
        )

        assert context.game_name == "My Game"
        assert context.synopsis == "An adventure game"
        assert context.source_language == "en"
        assert context.target_languages == ["ja", "ko"]
