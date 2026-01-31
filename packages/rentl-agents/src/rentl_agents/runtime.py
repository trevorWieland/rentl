"""Profile-driven agent runtime.

This module provides the generic agent runtime that executes agents
defined by TOML profiles.
"""

from __future__ import annotations

import asyncio
from typing import TypeVar

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from rentl_agents.layers import PromptComposer, PromptLayerRegistry
from rentl_agents.templates import TemplateContext
from rentl_agents.tools.registry import ToolRegistry
from rentl_core.ports.orchestrator import PhaseAgentProtocol
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.base import BaseSchema

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT = TypeVar("OutputT", bound=BaseSchema)


class ProfileAgentConfig(BaseSchema):
    """Configuration for profile-driven agent execution.

    Contains the runtime settings needed to execute an agent.
    """

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_id: str = "gpt-4o-mini"
    temperature: float = 0.7
    top_p: float = 1.0
    timeout_s: float = 60.0
    max_retries: int = 3
    retry_base_delay: float = 1.0


class ProfileAgent(PhaseAgentProtocol[InputT, OutputT]):
    """Generic agent driven by TOML profile configuration.

    This agent:
    - Loads prompts from a three-layer system (root → phase → agent)
    - Uses pydantic-ai for structured output
    - Supports tool registration from profile
    - Handles retries with exponential backoff
    """

    def __init__(
        self,
        profile: AgentProfileConfig,
        output_type: type[OutputT],
        layer_registry: PromptLayerRegistry,
        tool_registry: ToolRegistry,
        config: ProfileAgentConfig,
        template_context: TemplateContext | None = None,
    ) -> None:
        """Initialize the profile agent.

        Args:
            profile: Agent profile configuration.
            output_type: Expected output schema type.
            layer_registry: Prompt layer registry.
            tool_registry: Tool registry.
            config: Runtime configuration.
            template_context: Template context for prompt rendering.
        """
        self._profile = profile
        self._output_type = output_type
        self._layer_registry = layer_registry
        self._tool_registry = tool_registry
        self._config = config
        self._template_context = template_context or TemplateContext()
        self._composer = PromptComposer(registry=layer_registry)

    @property
    def profile(self) -> AgentProfileConfig:
        """Get the agent profile."""
        return self._profile

    @property
    def name(self) -> str:
        """Get the agent name."""
        return self._profile.meta.name

    def update_context(self, context: TemplateContext) -> None:
        """Update the template context.

        Args:
            context: New template context.
        """
        self._template_context = context

    async def run(self, payload: InputT) -> OutputT:
        """Execute the agent with the given payload.

        Args:
            payload: Input payload (phase-specific).

        Returns:
            OutputT: Agent output matching output_type.

        Raises:
            RuntimeError: If execution fails after retries.
        """
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                return await self._execute(payload)
            except Exception as exc:
                last_error = exc
                if attempt < self._config.max_retries:
                    delay = self._config.retry_base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        raise RuntimeError(
            f"Agent {self.name} execution failed after "
            f"{self._config.max_retries + 1} attempts"
        ) from last_error

    async def _execute(self, payload: InputT) -> OutputT:
        """Execute a single agent invocation.

        Args:
            payload: Input payload.

        Returns:
            Agent output.
        """
        # Build prompts from layers
        system_prompt = self._composer.compose_system_prompt(
            self._profile,
            self._template_context,
        )

        user_prompt = self._composer.render_user_prompt(
            self._profile,
            self._template_context,
        )

        # Get tools for this agent
        tool_callables = self._tool_registry.get_tool_callables(
            self._profile.tools.allowed
        )

        # Create pydantic-ai provider and model
        provider = OpenAIProvider(
            base_url=self._config.base_url,
            api_key=self._config.api_key,
        )
        model = OpenAIChatModel(self._config.model_id, provider=provider)

        model_settings: OpenAIChatModelSettings = {
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
            "timeout": self._config.timeout_s,
        }

        # Create agent with structured output
        agent: Agent[None, OutputT] = Agent(
            model=model,
            instructions=system_prompt,
            output_type=self._output_type,
            tools=tool_callables,  # type: ignore[arg-type]
        )

        result = await agent.run(user_prompt, model_settings=model_settings)
        return result.output
