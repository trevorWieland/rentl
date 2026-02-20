"""Unit tests for agent factory."""

from __future__ import annotations

import pytest
from pydantic import Field, ValidationError
from pydantic_ai import Tool

from rentl_agents.factory import AgentConfig, AgentFactory
from rentl_agents.harness import AgentHarness
from rentl_agents.tools import AgentTool, ContextLookupTool
from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import JsonValue


class MockInput(BaseSchema):
    """Mock input schema for testing."""

    text: str = Field(description="Source text to translate")
    target_lang: str = Field(description="Target language code")


class MockOutput(BaseSchema):
    """Mock output schema for testing."""

    result: str = Field(description="Translation result text")
    confidence: float = Field(description="Confidence score for the translation")


class MockTool(AgentTool):
    """Mock tool for testing."""

    def __init__(self) -> None:
        """Initialize mock tool for testing."""
        super().__init__(
            name="mock_tool",
            description="Mock tool for testing",
        )

    def execute(self, input_data: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Execute mock tool and return success result.

        Args:
            input_data: Tool input dictionary.

        Returns:
            Success result dictionary.
        """
        return {"result": "success", "tool_name": "mock_tool"}


class TestAgentConfig:
    """Test cases for AgentConfig class."""

    def test_create_valid_config(self) -> None:
        """Test creating a valid agent configuration."""
        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are a helpful assistant.",
            user_prompt_template="Translate: {{text}}",
        )

        assert config.model_endpoint_ref == "default"
        assert config.system_prompt == "You are a helpful assistant."
        assert config.user_prompt_template == "Translate: {{text}}"

    def test_create_config_with_tools(self) -> None:
        """Test creating a configuration with tools."""
        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            tools=["context_lookup", "glossary_search"],
        )

        assert config.tools == ["context_lookup", "glossary_search"]

    def test_create_config_with_retry_settings(self) -> None:
        """Test creating a configuration with retry settings."""
        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            max_retries=5,
            retry_base_delay=2.0,
        )

        assert config.max_retries == 5
        assert config.retry_base_delay == 2.0

    def test_create_config_with_empty_system_prompt(self) -> None:
        """Test creating config raises error for empty system prompt."""
        with pytest.raises(ValidationError, match="system_prompt"):
            AgentConfig(
                model_endpoint_ref="default",
                system_prompt="",
                user_prompt_template="Translate: {{text}}",
            )

    def test_create_config_with_empty_user_prompt_template(self) -> None:
        """Test creating config raises error for empty user prompt template."""
        with pytest.raises(ValidationError, match="user_prompt_template"):
            AgentConfig(
                model_endpoint_ref="default",
                system_prompt="You are helpful.",
                user_prompt_template="",
            )

    def test_create_config_with_empty_tool_name(self) -> None:
        """Test creating config raises error for empty tool name."""
        with pytest.raises(ValueError, match="Tool name must not be empty"):
            AgentConfig(
                model_endpoint_ref="default",
                system_prompt="You are helpful.",
                user_prompt_template="Translate: {{text}}",
                tools=["", "valid_tool"],
            )

    def test_create_config_with_invalid_max_retries(self) -> None:
        """Test creating config raises error for negative max_retries."""
        with pytest.raises(ValidationError, match="max_retries"):
            AgentConfig(
                model_endpoint_ref="default",
                system_prompt="You are helpful.",
                user_prompt_template="Translate: {{text}}",
                max_retries=-1,
            )

    def test_create_config_with_invalid_retry_base_delay(self) -> None:
        """Test creating config raises error for non-positive retry_base_delay."""
        with pytest.raises(ValidationError, match="retry_base_delay"):
            AgentConfig(
                model_endpoint_ref="default",
                system_prompt="You are helpful.",
                user_prompt_template="Translate: {{text}}",
                retry_base_delay=0.0,
            )


class TestAgentFactory:
    """Test cases for AgentFactory class."""

    def test_create_factory(self) -> None:
        """Test creating a factory."""
        factory = AgentFactory()

        assert factory._tool_registry == {}
        assert factory._instance_cache == {}

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        factory = AgentFactory()

        factory.register_tool("mock_tool", lambda: MockTool())

        assert "mock_tool" in factory._tool_registry

    def test_register_duplicate_tool(self) -> None:
        """Test registering a duplicate tool raises error."""
        factory = AgentFactory()

        factory.register_tool("mock_tool", lambda: MockTool())

        with pytest.raises(ValueError, match="Tool mock_tool is already registered"):
            factory.register_tool("mock_tool", lambda: MockTool())

    def test_unregister_tool(self) -> None:
        """Test unregistering a tool."""
        factory = AgentFactory()

        factory.register_tool("mock_tool", lambda: MockTool())
        factory.unregister_tool("mock_tool")

        assert "mock_tool" not in factory._tool_registry

    def test_unregister_nonexistent_tool(self) -> None:
        """Test unregistering a nonexistent tool does not raise error."""
        factory = AgentFactory()

        factory.unregister_tool("nonexistent_tool")

    def test_create_agent_success(self) -> None:
        """Test creating an agent successfully."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        agent = factory.create_agent(config, MockOutput)

        assert isinstance(agent, AgentHarness)

    def test_create_agent_with_tools(self) -> None:
        """Test creating an agent with tools."""
        factory = AgentFactory()

        factory.register_tool("context_lookup", lambda: ContextLookupTool())

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            tools=["context_lookup"],
        )

        agent = factory.create_agent(config, MockOutput)

        assert isinstance(agent, AgentHarness)

    def test_create_agent_with_unregistered_tool(self) -> None:
        """Test creating agent with unregistered tool raises error."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            tools=["unregistered_tool"],
        )

        with pytest.raises(
            ValueError, match="Tool unregistered_tool is not registered"
        ):
            factory.create_agent(config, MockOutput)

    def test_create_agent_caching(self) -> None:
        """Test that agent instances are cached."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        agent1 = factory.create_agent(config, MockOutput)
        agent2 = factory.create_agent(config, MockOutput)

        assert agent1 is agent2

    def test_create_pool_with_invalid_count(self) -> None:
        """Test creating pool with invalid count raises error."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        with pytest.raises(ValueError, match="count must be positive"):
            factory.create_pool(config, MockOutput, count=0)

    def test_create_pool_success(self) -> None:
        """Test creating an agent pool successfully."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        pool = factory.create_pool(config, MockOutput, count=4)

        assert pool is not None

    def test_create_pool_with_max_parallel(self) -> None:
        """Test creating an agent pool with max_parallel setting."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        pool = factory.create_pool(
            config,
            MockOutput,
            count=4,
            max_parallel=2,
        )

        assert pool is not None

    def test_clear_cache(self) -> None:
        """Test clearing the agent instance cache."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        agent1 = factory.create_agent(config, MockOutput)
        factory.clear_cache()
        agent2 = factory.create_agent(config, MockOutput)

        assert agent1 is not agent2

    def test_build_cache_key(self) -> None:
        """Test building cache key is deterministic."""
        factory = AgentFactory()

        config = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        key1 = factory._build_cache_key(config, MockOutput)
        key2 = factory._build_cache_key(config, MockOutput)

        assert key1 == key2

    def test_build_cache_key_different_config(self) -> None:
        """Test cache keys are different for different configs."""
        factory = AgentFactory()

        config1 = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
        )

        config2 = AgentConfig(
            model_endpoint_ref="default",
            system_prompt="You are a translator.",
            user_prompt_template="Translate: {{text}}",
        )

        key1 = factory._build_cache_key(config1, MockOutput)
        key2 = factory._build_cache_key(config2, MockOutput)

        assert key1 != key2

    def test_build_tool_list(self) -> None:
        """Test building tool list produces Tool objects with explicit names."""
        factory = AgentFactory()

        factory.register_tool("mock_tool", lambda: MockTool())

        tool_list = factory._build_tool_list(["mock_tool"])

        assert len(tool_list) == 1
        assert isinstance(tool_list[0], Tool)
        assert tool_list[0].name == "mock_tool"

    def test_build_tool_list_preserves_description(self) -> None:
        """Test Tool objects carry the original tool description."""
        factory = AgentFactory()

        factory.register_tool("mock_tool", lambda: MockTool())

        tool_list = factory._build_tool_list(["mock_tool"])

        assert tool_list[0].description == "Mock tool for testing"

    def test_build_tool_list_multiple_tools(self) -> None:
        """Test building tool list with multiple tools produces named Tool objects."""
        factory = AgentFactory()

        factory.register_tool("mock_tool", lambda: MockTool())
        factory.register_tool("context_lookup", lambda: ContextLookupTool())

        tool_list = factory._build_tool_list(["mock_tool", "context_lookup"])

        assert len(tool_list) == 2
        assert all(isinstance(t, Tool) for t in tool_list)
        names = [t.name for t in tool_list]
        assert names == ["mock_tool", "context_lookup"]

    def test_build_tool_list_with_unregistered_tool(self) -> None:
        """Test building tool list raises error for unregistered tool."""
        factory = AgentFactory()

        with pytest.raises(
            ValueError, match="Tool unregistered_tool is not registered"
        ):
            factory._build_tool_list(["unregistered_tool"])
