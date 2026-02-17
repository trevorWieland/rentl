"""Agent harness for pydantic-ai integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from rentl_agents.prompts import PromptRenderer
from rentl_core.ports.orchestrator import PhaseAgentProtocol
from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import JsonValue

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT_co = TypeVar("OutputT_co", bound=BaseSchema, covariant=True)


@runtime_checkable
class AgentHarnessProtocol(Protocol[InputT, OutputT_co]):
    """Protocol for agent harness implementation."""

    async def run(self, payload: InputT) -> OutputT_co:
        """Execute the agent with the given payload."""
        raise NotImplementedError

    async def initialize(self, config: AgentHarnessConfig) -> None:
        """Initialize the agent with configuration."""
        raise NotImplementedError

    def validate_input(self, input_data: InputT) -> bool:
        """Validate input schema."""
        raise NotImplementedError

    def validate_output(self, output_data: BaseSchema) -> bool:
        """Validate output schema."""
        raise NotImplementedError


class AgentHarnessConfig(BaseSchema):
    """Configuration for agent harness initialization."""

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_id: str
    temperature: float = 0.7
    top_p: float = 1.0
    timeout_s: float = 30.0
    max_output_tokens: int = 4096


class AgentHarness(PhaseAgentProtocol[InputT, OutputT_co]):
    """Base agent harness with pydantic-ai integration.

    This harness wraps a pydantic-ai Agent with additional functionality:
    - Prompt template rendering
    - Tool registration and execution
    - Error handling with retry logic
    - Input/output validation

    Args:
        system_prompt: System prompt for the agent.
        user_prompt_template: User prompt template with variable substitution.
        output_type: Type hint for output schema.
        tools: Optional list of tool callables to register.
        max_retries: Maximum retry attempts for transient failures.
        retry_base_delay: Base delay for exponential backoff in seconds.
    """

    def __init__(
        self,
        system_prompt: str,
        user_prompt_template: str,
        output_type: type[OutputT_co],
        tools: list[Callable[..., dict[str, JsonValue]]] | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        """Initialize the agent harness.

        Args:
            system_prompt: System prompt for the agent.
            user_prompt_template: User prompt template with variable substitution.
            output_type: Type hint for output schema.
            tools: Optional list of tool callables to register.
            max_retries: Maximum retry attempts for transient failures.
            retry_base_delay: Base delay for exponential backoff in seconds.

        Raises:
            ValueError: If system_prompt or user_prompt_template is invalid.
        """
        if not system_prompt:
            raise ValueError("system_prompt must not be empty")
        if not user_prompt_template:
            raise ValueError("user_prompt_template must not be empty")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_base_delay <= 0:
            raise ValueError("retry_base_delay must be positive")

        self._system_prompt = system_prompt
        self._user_prompt_template = user_prompt_template
        self._output_type = output_type
        self._tools = tools or []
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._renderer = PromptRenderer()
        self._config: AgentHarnessConfig | None = None

    @property
    def initialized(self) -> bool:
        """Check if the harness is initialized."""
        return self._config is not None

    async def initialize(self, config: AgentHarnessConfig) -> None:
        """Initialize agent with configuration.

        Args:
            config: Configuration for the agent.
        """
        self._config = config

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

    def validate_output(self, output_data: BaseSchema) -> bool:
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

    async def run(self, payload: InputT) -> OutputT_co:
        """Execute the agent with the given payload.

        Args:
            payload: Input payload for the agent.

        Returns:
            OutputT: Agent output.

        Raises:
            ValueError: If agent is not initialized.
            RuntimeError: If agent execution fails after retries.
        """
        if self._config is None:
            raise ValueError("Agent must be initialized before running")

        self.validate_input(payload)

        user_prompt = self._renderer.render_template(
            self._user_prompt_template,
            payload.model_dump(),
        )

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                result = await self._execute_agent(user_prompt)
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

    async def _execute_agent(self, user_prompt: str) -> OutputT_co:
        """Execute the agent prompt using pydantic-ai.

        Creates a fresh Agent instance for each execution, following the
        pattern used in OpenAICompatibleRuntime. This ensures proper typing
        as pydantic-ai infers the output type from the Agent constructor.

        Args:
            user_prompt: Rendered user prompt.

        Returns:
            OutputT: Agent output.

        Raises:
            RuntimeError: If agent execution fails.
        """
        if self._config is None:
            raise RuntimeError("Agent not initialized")

        provider = OpenAIProvider(
            base_url=self._config.base_url,
            api_key=self._config.api_key,
        )
        model = OpenAIChatModel(self._config.model_id, provider=provider)

        model_settings: OpenAIChatModelSettings = {
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
            "timeout": self._config.timeout_s,
            "max_tokens": self._config.max_output_tokens,
        }

        agent: Agent[None, OutputT_co] = Agent[None, OutputT_co](
            model=model,
            instructions=self._system_prompt,
            output_type=self._output_type,
            tools=self._tools,
        )

        result = await agent.run(user_prompt, model_settings=model_settings)
        return result.output
