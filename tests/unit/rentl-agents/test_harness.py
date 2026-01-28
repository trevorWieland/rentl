"""Unit tests for agent harness."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rentl_agents.harness import AgentHarness
from rentl_schemas.base import BaseSchema


class MockInput(BaseSchema):
    """Mock input schema for testing."""

    text: str
    target_lang: str


class MockOutput(BaseSchema):
    """Mock output schema for testing."""

    result: str
    confidence: float


class TestAgentHarness:
    """Test cases for AgentHarness class."""

    def test_initialize_with_valid_params(self) -> None:
        """Test agent harness initialization with valid parameters."""
        mock_runtime = MagicMock(spec=[])
        harness = AgentHarness(
            runtime=mock_runtime,
            system_prompt="You are a helpful assistant.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        assert harness._system_prompt == "You are a helpful assistant."
        assert harness._user_prompt_template == "Translate: {{text}}"
        assert harness._output_type == MockOutput
        assert harness._max_retries == 3
        assert harness._retry_base_delay == 1.0
        assert not harness._initialized

    def test_initialize_with_invalid_system_prompt(self) -> None:
        """Test initialization raises error for empty system prompt."""
        mock_runtime = MagicMock(spec=[])

        with pytest.raises(ValueError, match="system_prompt must not be empty"):
            AgentHarness(
                runtime=mock_runtime,
                system_prompt="",
                user_prompt_template="Translate: {{text}}",
                output_type=MockOutput,
            )

    def test_initialize_with_invalid_user_prompt_template(self) -> None:
        """Test initialization raises error for empty user prompt template."""
        mock_runtime = MagicMock(spec=[])

        with pytest.raises(ValueError, match="user_prompt_template must not be empty"):
            AgentHarness(
                runtime=mock_runtime,
                system_prompt="You are helpful.",
                user_prompt_template="",
                output_type=MockOutput,
            )

    def test_initialize_with_invalid_max_retries(self) -> None:
        """Test initialization raises error for negative max_retries."""
        mock_runtime = MagicMock(spec=[])

        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            AgentHarness(
                runtime=mock_runtime,
                system_prompt="You are helpful.",
                user_prompt_template="Translate: {{text}}",
                output_type=MockOutput,
                max_retries=-1,
            )

    def test_initialize_with_invalid_retry_base_delay(self) -> None:
        """Test initialization raises error for zero or negative retry_base_delay."""
        mock_runtime = MagicMock(spec=[])

        with pytest.raises(ValueError, match="retry_base_delay must be positive"):
            AgentHarness(
                runtime=mock_runtime,
                system_prompt="You are helpful.",
                user_prompt_template="Translate: {{text}}",
                output_type=MockOutput,
                retry_base_delay=0.0,
            )

    @pytest.mark.asyncio
    async def test_initialize_with_config(self) -> None:
        """Test agent initialization with configuration."""
        mock_runtime = MagicMock(spec=[])
        harness = AgentHarness(
            runtime=mock_runtime,
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = {"api_key": "test-key", "model_settings": {}}

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            await harness.initialize(config)

        assert harness._initialized is True
        assert harness._agent is not None

    @pytest.mark.asyncio
    async def test_initialize_without_api_key(self) -> None:
        """Test initialization raises error without API key."""
        mock_runtime = MagicMock(spec=[])
        harness = AgentHarness(
            runtime=mock_runtime,
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        config = {"model_settings": {}}

        with pytest.raises(ValueError, match="api_key is required"):
            await harness.initialize(config)

    def test_validate_input_with_valid_data(self) -> None:
        """Test input validation with valid data."""
        mock_runtime = MagicMock(spec=[])
        harness = AgentHarness(
            runtime=mock_runtime,
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
        )

        input_data = MockInput(text="Hello", target_lang="ja")

        result = harness.validate_input(input_data)

        assert result is True

    def test_validate_output_with_valid_data(self) -> None:
        """Test output validation with valid data."""
        mock_runtime = MagicMock(spec=[])
        harness = AgentHarness(
            runtime=mock_runtime,
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
        mock_runtime = MagicMock(spec=[])
        harness = AgentHarness(
            runtime=mock_runtime,
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
    async def test_run_raises_error_after_max_retries(self) -> None:
        """Test run raises error after exhausting retries."""
        mock_runtime = MagicMock()
        mock_runtime.run_prompt = AsyncMock(side_effect=Exception("Persistent error"))

        harness = AgentHarness(
            runtime=mock_runtime,
            system_prompt="You are helpful.",
            user_prompt_template="Translate: {{text}}",
            output_type=MockOutput,
            max_retries=2,
            retry_base_delay=0.01,
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            await harness.initialize({"api_key": "test-key", "model_settings": {}})

        input_data = MockInput(text="Hello", target_lang="ja")

        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await harness.run(input_data)

        assert mock_runtime.run_prompt.call_count == 3
