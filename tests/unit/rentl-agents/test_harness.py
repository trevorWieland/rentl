"""Unit tests for agent harness."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import Field, ValidationError
from pydantic_ai import Tool

from rentl_agents.harness import AgentHarness, AgentHarnessConfig
from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import JsonValue


class MockInput(BaseSchema):
    """Mock input schema for testing."""

    text: str = Field(..., description="Text to process")
    target_lang: str = Field(..., description="Target language code")


class MockOutput(BaseSchema):
    """Mock output schema for testing."""

    result: str = Field(..., description="Processed result")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class TestAgentHarness:
    """Test cases for AgentHarness class."""

    def test_initialize_with_valid_params(self) -> None:
        """Test agent harness initialization with valid parameters."""
        harness = AgentHarness(
            system_prompt="You are a helpful assistant.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        assert harness._system_prompt == "You are a helpful assistant."
        assert harness._user_prompt_template == "Translate: {{text}}"
        assert harness._output_type == MockOutput
        assert harness._max_retries == 3
        assert harness._retry_base_delay == 1.0
        assert not harness.initialized

    def test_initialize_with_invalid_system_prompt(self) -> None:
        """Test initialization raises error for empty system prompt."""
        with pytest.raises(ValueError, match="system_prompt must not be empty"):
            AgentHarness(
                system_prompt="",
                user_prompt_template="Translate: {{text}}",
                output_type=MockOutput,
            )

    def test_initialize_with_invalid_user_prompt_template(self) -> None:
        """Test initialization raises error for empty user prompt template."""
        with pytest.raises(ValueError, match="user_prompt_template must not be empty"):
            AgentHarness(
                system_prompt="You are helpful.",
                user_prompt_template="",
                output_type=MockOutput,
            )

    def test_initialize_with_invalid_max_retries(self) -> None:
        """Test initialization raises error for negative max_retries."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            AgentHarness(
                system_prompt="You are helpful.",
                user_prompt_template="Translate: {{text}}",
                output_type=MockOutput,
                max_retries=-1,
            )

    def test_initialize_with_invalid_retry_base_delay(self) -> None:
        """Test initialization raises error for zero or negative retry_base_delay."""
        with pytest.raises(ValueError, match="retry_base_delay must be positive"):
            AgentHarness(
                system_prompt="You are helpful.",
                user_prompt_template="Translate: {{text}}",
                output_type=MockOutput,
                retry_base_delay=0.0,
            )

    @pytest.mark.asyncio
    async def test_initialize_with_config(self) -> None:
        """Test agent initialization with configuration."""
        harness = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")

        await harness.initialize(config)

        assert harness.initialized is True
        assert harness._config is not None
        assert harness._config.api_key == "test-key"

    def test_validate_input_with_valid_data(self) -> None:
        """Test input validation with valid data."""
        harness = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        input_data = MockInput(text="Hello", target_lang="ja")

        result = harness.validate_input(input_data)

        assert result is True

    def test_validate_output_with_valid_data(self) -> None:
        """Test output validation with valid data."""
        harness = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        output_data = MockOutput(result="こんにちは", confidence=0.95)

        result = harness.validate_output(output_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_run_without_initialization(self) -> None:
        """Test run raises error if agent is not initialized."""
        harness = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        input_data = MockInput(text="Hello", target_lang="ja")

        with pytest.raises(
            ValueError, match="Agent must be initialized before running"
        ):
            await harness.run(input_data)

    @pytest.mark.asyncio
    async def test_run_returns_output_on_success(self) -> None:
        """Test successful execution returns valid output (happy path)."""
        harness = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}} to {{target_lang}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        expected_output = MockOutput(result="こんにちは", confidence=0.95)

        # Mock _execute_agent to return the expected output
        with patch.object(
            harness, "_execute_agent", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = expected_output

            input_data = MockInput(text="Hello", target_lang="ja")
            result = await harness.run(input_data)

            assert result.result == "こんにちは"
            assert result.confidence == 0.95
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_raises_error_after_max_retries(self) -> None:
        """Test run raises error after exhausting retries."""
        harness = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
            max_retries=2,
            retry_base_delay=0.01,
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        # Mock _execute_agent to always fail
        with patch.object(
            harness, "_execute_agent", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = Exception("Persistent error")

            input_data = MockInput(text="Hello", target_lang="ja")

            with pytest.raises(RuntimeError, match="Agent execution failed"):
                await harness.run(input_data)

            # Should have tried 3 times (initial + 2 retries)
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_tools_registered_with_harness(self) -> None:
        """Test Tool objects are stored in harness during initialization."""

        def mock_tool_fn(query: str) -> dict[str, JsonValue]:
            return {"result": f"Result for {query}"}

        mock_tool = Tool(mock_tool_fn, name="mock_search", takes_ctx=False)

        harness = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Search: {{text}}",
            output_type=MockOutput,
            tools=[mock_tool],
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        # Verify the harness stored the tools
        assert len(harness._tools) == 1
        assert isinstance(harness._tools[0], Tool)
        assert harness._tools[0].name == "mock_search"

    @pytest.mark.asyncio
    async def test_run_with_tools_executes_successfully(self) -> None:
        """Test agent run with Tool objects registered completes successfully."""

        def mock_tool_fn(query: str) -> dict[str, JsonValue]:
            return {"result": f"Result for {query}"}

        mock_tool = Tool(mock_tool_fn, name="mock_process", takes_ctx=False)

        harness = AgentHarness(
            system_prompt="You are helpful with tools.",
            user_prompt_template="Process: {{text}}",
            output_type=MockOutput,
            tools=[mock_tool],
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        expected_output = MockOutput(result="Processed", confidence=0.9)

        with patch.object(
            harness, "_execute_agent", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = expected_output

            input_data = MockInput(text="Hello", target_lang="en")
            result = await harness.run(input_data)

            assert result.result == "Processed"
            assert result.confidence == 0.9


class TestAgentHarnessExecuteAgent:
    """Test cases for _execute_agent integration with pydantic-ai.

    These tests mock the centralized create_model factory and Agent class,
    ensuring the core execution logic is properly tested.
    """

    @staticmethod
    def _agent_shim(mock_agent_cls: MagicMock) -> type:
        class AgentShim:
            @classmethod
            def __class_getitem__(cls, _params: object) -> type:
                return cls

            def __new__(cls, *args: object, **kwargs: object) -> MagicMock:
                return mock_agent_cls(*args, **kwargs)

        return AgentShim

    @pytest.mark.asyncio
    async def test_execute_agent_creates_provider_with_config(self) -> None:
        """Verify create_model factory is called with correct config."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(
            api_key="test-api-key",
            base_url="https://custom.api.com/v1",
            model_id="gpt-5-nano",
        )
        await harness.initialize(config)

        mock_result = MagicMock()
        mock_result.output = MockOutput(result="translated", confidence=0.9)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.7}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ) as mock_factory,
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="Hello", target_lang="ja")
            await harness.run(input_data)

            mock_factory.assert_called_once()
            call_kwargs = mock_factory.call_args.kwargs
            assert call_kwargs["base_url"] == "https://custom.api.com/v1"
            assert call_kwargs["api_key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_execute_agent_creates_model_with_config(self) -> None:
        """Verify create_model factory is called with correct model_id."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(
            api_key="test-key",
            model_id="gpt-5-nano",
        )
        await harness.initialize(config)

        mock_result = MagicMock()
        mock_result.output = MockOutput(result="translated", confidence=0.9)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.7}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ) as mock_factory,
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="Hello", target_lang="ja")
            await harness.run(input_data)

            mock_factory.assert_called_once()
            assert mock_factory.call_args.kwargs["model_id"] == "gpt-5-nano"

    @pytest.mark.asyncio
    async def test_execute_agent_passes_tools_to_agent(self) -> None:
        """Verify Tool objects are passed to Agent constructor.

        This is the critical test that ensures Tool objects registered with the
        harness are actually passed to the underlying pydantic-ai Agent, not
        raw callables.
        """

        def mock_tool_fn(query: str) -> dict[str, JsonValue]:
            """Mock tool function for testing.

            Args:
                query: The query string.

            Returns:
                A formatted result string.
            """
            return {"result": f"Result for {query}"}

        mock_tool = Tool(
            mock_tool_fn, name="mock_search", description="Search tool", takes_ctx=False
        )
        tools_list: list[Tool] = [mock_tool]

        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are a helpful assistant.",
            user_prompt_template="Process: {{text}}",
            output_type=MockOutput,
            tools=tools_list,
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        mock_result = MagicMock()
        mock_result.output = MockOutput(result="processed", confidence=0.85)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.7}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ),
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="Hello", target_lang="en")
            await harness.run(input_data)

            # Verify Agent was called with Tool objects, not raw callables
            mock_agent_cls.assert_called_once()
            call_kwargs = mock_agent_cls.call_args.kwargs
            assert "tools" in call_kwargs
            assert call_kwargs["tools"] == tools_list
            assert isinstance(call_kwargs["tools"][0], Tool)
            assert call_kwargs["tools"][0].name == "mock_search"

    @pytest.mark.asyncio
    async def test_execute_agent_creates_agent_with_correct_params(self) -> None:
        """Verify Agent is created with model, instructions, output_type, and tools."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are a translation assistant.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        mock_result = MagicMock()
        mock_result.output = MockOutput(result="translated", confidence=0.95)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.7}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ),
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="Hello", target_lang="ja")
            await harness.run(input_data)

            mock_agent_cls.assert_called_once_with(
                model=mock_model,
                instructions="You are a translation assistant.",
                output_type=MockOutput,
                tools=[],
                output_retries=3,
            )

    @pytest.mark.asyncio
    async def test_execute_agent_calls_run_with_prompt_and_settings(self) -> None:
        """Verify agent.run() is called with rendered prompt and model settings."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}} to {{target_lang}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(
            api_key="test-key",
            model_id="gpt-5-nano",
            temperature=0.5,
            top_p=0.9,
            timeout_s=60.0,
        )
        await harness.initialize(config)

        mock_result = MagicMock()
        mock_result.output = MockOutput(result="こんにちは", confidence=0.98)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.5, "top_p": 0.9, "timeout": 60.0}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ),
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="Hello", target_lang="ja")
            await harness.run(input_data)

            mock_agent_instance.run.assert_called_once()
            call_args = mock_agent_instance.run.call_args

            # Verify user prompt was rendered correctly
            assert call_args.args[0] == "Translate: Hello to ja"

            # Verify model settings from factory are passed through
            model_settings = call_args.kwargs["model_settings"]
            assert model_settings["temperature"] == 0.5
            assert model_settings["top_p"] == 0.9
            assert model_settings["timeout"] == 60.0

    @pytest.mark.asyncio
    async def test_execute_agent_returns_result_output(self) -> None:
        """Verify _execute_agent returns result.output from agent.run()."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Process: {{text}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        expected_output = MockOutput(result="processed text", confidence=0.92)
        mock_result = MagicMock()
        mock_result.output = expected_output

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.7}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ),
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="hello", target_lang="en")
            result = await harness.run(input_data)

            assert result == expected_output
            assert result.result == "processed text"
            assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_execute_agent_raises_on_uninitialized(self) -> None:
        """Verify _execute_agent raises RuntimeError if not initialized."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        # Call _execute_agent directly without initializing
        with pytest.raises(RuntimeError, match="Agent not initialized"):
            await harness._execute_agent("test prompt")

    @pytest.mark.asyncio
    async def test_execute_agent_passes_output_retries_from_config(self) -> None:
        """Verify output_retries from config is passed to Agent constructor."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(
            api_key="test-key",
            model_id="gpt-5-nano",
            output_retries=5,
        )
        await harness.initialize(config)

        mock_result = MagicMock()
        mock_result.output = MockOutput(result="translated", confidence=0.9)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.7}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ),
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="Hello", target_lang="ja")
            await harness.run(input_data)

            mock_agent_cls.assert_called_once()
            call_kwargs = mock_agent_cls.call_args.kwargs
            assert call_kwargs["output_retries"] == 5

    @pytest.mark.asyncio
    async def test_execute_agent_default_output_retries(self) -> None:
        """Verify default output_retries is 3 when not specified in config."""
        harness: AgentHarness[MockInput, MockOutput] = AgentHarness(
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = AgentHarnessConfig(api_key="test-key", model_id="gpt-5-nano")
        await harness.initialize(config)

        mock_result = MagicMock()
        mock_result.output = MockOutput(result="translated", confidence=0.9)

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        mock_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_model = MagicMock()
        mock_settings = {"temperature": 0.7}

        with (
            patch(
                "rentl_agents.harness.create_model",
                return_value=(mock_model, mock_settings),
            ),
            patch("rentl_agents.harness.Agent", self._agent_shim(mock_agent_cls)),
        ):
            input_data = MockInput(text="Hello", target_lang="ja")
            await harness.run(input_data)

            mock_agent_cls.assert_called_once()
            call_kwargs = mock_agent_cls.call_args.kwargs
            assert call_kwargs["output_retries"] == 3


class TestAgentHarnessConfigValidation:
    """Test cases for AgentHarnessConfig field validation."""

    def test_model_id_required(self) -> None:
        """Omitting model_id raises ValidationError."""
        with pytest.raises(ValidationError, match="model_id"):
            AgentHarnessConfig(api_key="test-key")  # type: ignore[call-arg]
