"""Agent harness for pydantic-ai integration."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModelSettings

from rentl_agents.prompts import PromptRenderer
from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_core.ports.orchestrator import PhaseAgentProtocol
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import RetryConfig
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmPromptResponse,
    LlmRuntimeSettings,
)

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT = TypeVar("OutputT", bound=BaseSchema)


@runtime_checkable
class AgentHarnessProtocol(Protocol[InputT, OutputT]):
    """Protocol for agent harness implementation."""

    async def run(self, payload: InputT) -> OutputT:
        """Execute the agent with the given payload."""
        raise NotImplementedError

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        raise NotImplementedError

    def validate_input(self, input_data: InputT) -> bool:
        """Validate input schema."""
        raise NotImplementedError

    def validate_output(self, output_data: OutputT) -> bool:
        """Validate output schema."""
        raise NotImplementedError


class AgentHarness(PhaseAgentProtocol[InputT, OutputT]):
    """Base agent harness with pydantic-ai integration.

    This harness wraps a pydantic-ai Agent with additional functionality:
    - LLM runtime integration
    - Prompt template rendering
    - Tool registration and execution
    - Error handling with retry logic
    - Input/output validation

    Args:
        runtime: LLM runtime for executing prompts.
        system_prompt: System prompt for the agent.
        user_prompt_template: User prompt template with variable substitution.
        output_type: Type hint for output schema.
        tools: Optional list of tool functions to register.
        max_retries: Maximum retry attempts for transient failures.
        retry_base_delay: Base delay for exponential backoff in seconds.
    """

    def __init__(
        self,
        runtime: LlmRuntimeProtocol,
        system_prompt: str,
        user_prompt_template: str,
        output_type: type[OutputT],
        tools: list[dict[str, Any]] | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize the agent harness.

        Args:
            runtime: LLM runtime for executing prompts.
            system_prompt: System prompt for the agent.
            user_prompt_template: User prompt template with variable substitution.
            output_type: Type hint for output schema.
            tools: Optional list of tool functions to register.
            max_retries: Maximum retry attempts for transient failures.
            retry_base_delay: Base delay for exponential backoff in seconds.

        Raises:
            ValueError: If runtime, system_prompt, or user_prompt_template is invalid.
        """
        if not system_prompt:
            raise ValueError("system_prompt must not be empty")
        if not user_prompt_template:
            raise ValueError("user_prompt_template must not be empty")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_base_delay <= 0:
            raise ValueError("retry_base_delay must be positive")

        self._runtime = runtime
        self._system_prompt = system_prompt
        self._user_prompt_template = user_prompt_template
        self._output_type = output_type
        self._tools = tools or []
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._renderer = PromptRenderer()
        self._agent: Agent[OutputT] | None = None
        self._initialized = False

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize agent with configuration.

        Args:
            config: Configuration dictionary with settings.

        Raises:
            ValueError: If configuration is invalid.
        """
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("api_key is required in configuration")

        model_settings = config.get("model_settings", {})

        self._agent = Agent(
            model="openai:gpt-4o-mini",
            system_prompt=self._system_prompt,
            output_type=self._output_type,
            model_settings=OpenAIChatModelSettings(**model_settings),
            tools=[tool.get("execute") for tool in self._tools if tool.get("execute")],
        )

        self._initialized = True

    def validate_input(self, input_data: InputT) -> bool:
        """Validate input schema.

        Args:
            input_data: Input payload to validate.

        Returns:
            True if validation passes.

        Raises:
            ValidationError: If input data is invalid.
        """
        if not isinstance(input_data, BaseSchema):
            raise ValidationError("Input must be a Pydantic BaseSchema")
        input_data.model_validate(input_data.model_dump())
        return True

    def validate_output(self, output_data: OutputT) -> bool:
        """Validate output schema.

        Args:
            output_data: Output payload to validate.

        Returns:
            True if validation passes.

        Raises:
            ValidationError: If output data is invalid.
        """
        if not isinstance(output_data, BaseSchema):
            raise ValidationError("Output must be a Pydantic BaseSchema")
        self._output_type.model_validate(output_data.model_dump())
        return True

    async def run(self, payload: InputT) -> OutputT:
        """Execute the agent with the given payload.

        Args:
            payload: Input payload for the agent.

        Returns:
            OutputT: Agent output.

        Raises:
            ValueError: If agent is not initialized.
            RuntimeError: If agent execution fails after retries.
        """
        if not self._initialized or self._agent is None:
            raise ValueError("Agent must be initialized before running")

        self.validate_input(payload)

        user_prompt = self._renderer.render_template(
            self._user_prompt_template,
            payload.model_dump(),
        )

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                result = await self._run_with_retry(user_prompt)
                self.validate_output(result)
                return result
            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._retry_base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    raise RuntimeError(
                        f"Agent execution failed after {self._max_retries + 1} attempts"
                    ) from last_error

        raise RuntimeError("Agent execution failed") from last_error

    async def _run_with_retry(self, user_prompt: str) -> OutputT:
        """Execute the agent prompt with retry logic.

        Args:
            user_prompt: Rendered user prompt.

        Returns:
            OutputT: Agent output.

        Raises:
            RuntimeError: If agent execution fails.
        """
        request = LlmPromptRequest(
            runtime=self._build_runtime_config(),
            system_prompt=self._system_prompt,
            prompt=user_prompt,
        )

        api_key = "dummy"

        response: LlmPromptResponse = await self._runtime.run_prompt(
            request, api_key=api_key
        )

        try:
            output_dict = self._parse_output(response.output_text)
            return self._output_type(**output_dict)
        except (ValueError, TypeError, ValidationError) as exc:
            raise RuntimeError(f"Failed to parse agent output: {exc}") from exc

    def _build_runtime_config(self) -> LlmRuntimeSettings:
        """Build runtime configuration for LLM.

        Returns:
            Runtime configuration settings.
        """
        return LlmRuntimeSettings(
            endpoint=LlmEndpointTarget(
                provider_name="openai",
                base_url="https://api.openai.com/v1",
                api_key_env="OPENAI_API_KEY",
                timeout_s=30.0,
            ),
            model=LlmModelSettings(
                model_id="gpt-4o-mini",
                temperature=0.7,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0,
            ),
            retry=RetryConfig(
                max_retries=3,
                backoff_s=1.0,
                max_backoff_s=30.0,
            ),
        )

    def _parse_output(self, output_text: str) -> dict[str, Any]:
        """Parse agent output text into a dictionary.

        Args:
            output_text: Raw output text from the agent.

        Returns:
            Parsed output dictionary.

        Raises:
            ValueError: If output cannot be parsed.
        """
        import json

        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Output is not valid JSON: {output_text}") from exc
