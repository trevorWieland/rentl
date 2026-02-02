"""Profile-driven agent runtime.

This module provides the generic agent runtime that executes agents
defined by TOML profiles.
"""

from __future__ import annotations

import asyncio
from typing import Literal, TypeVar

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.output import PromptedOutput
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.usage import UsageLimits

from rentl_agents.layers import PromptComposer, PromptLayerRegistry
from rentl_agents.templates import TemplateContext
from rentl_agents.tools.registry import ToolRegistry
from rentl_core.ports.orchestrator import PhaseAgentProtocol
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.base import BaseSchema

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT = TypeVar("OutputT", bound=BaseSchema)

# Output mode for structured output
# - "auto": Auto-detect based on provider (recommended)
# - "prompted": Uses response_format with json_schema (OpenRouter, most cloud APIs)
# - "tool": Uses tool calling with tool_choice:required (LM Studio, OpenAI)
# - "native": Uses model's native structured output (OpenAI only)
#
# Provider compatibility:
# - OpenRouter: "prompted" (no tool_choice:required support)
# - LM Studio: "tool" (has tool_choice:required, json_schema may have issues)
# - OpenAI: both work, "tool" is default pydantic-ai behavior
OutputMode = Literal["auto", "prompted", "tool", "native"]


class ProfileAgentConfig(BaseSchema):
    """Configuration for profile-driven agent execution.

    Contains the runtime settings needed to execute an agent.
    """

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_id: str = "gpt-4o-mini"
    temperature: float = 0.7
    top_p: float = 1.0
    timeout_s: float = 180.0
    max_retries: int = 2  # Retries for transient errors only (network, rate limits)
    retry_base_delay: float = 2.0
    output_mode: OutputMode = "auto"  # Auto-detect based on provider
    # Safeguards against infinite loops - FAIL LOUDLY when exceeded
    # Note: pydantic-ai default is 50, but we use a lower limit to control costs
    # and detect problematic prompts/schemas earlier
    max_requests_per_run: int = (
        20  # Max API requests per single run - includes output validation retries
    )
    # Output validation retries (pydantic-ai provides feedback to model)
    max_output_retries: int = 5


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
            RuntimeError: If execution fails (transient errors, validation failures,
                or usage limits exceeded). Error message indicates the cause.
        """
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                return await self._execute(payload)
            except UsageLimitExceeded as e:
                # Model failed to produce valid output within request limit
                # This is a LOUD failure - don't retry, report clearly
                limit = self._config.max_requests_per_run
                raise RuntimeError(
                    f"Agent {self.name} FAILED: Hit request limit ({limit}). "
                    f"Model repeatedly failed to produce valid structured output. "
                    f"The model may not be capable enough for this task. "
                    f"Try a more capable model (e.g., gpt-4o, claude-3.5-sonnet). "
                    f"Details: {e}"
                ) from e
            except UnexpectedModelBehavior as e:
                # Model produced invalid output that couldn't be parsed
                # This is a LOUD failure - don't retry, report clearly
                raise RuntimeError(
                    f"Agent {self.name} FAILED: Model produced invalid output. "
                    f"The model response did not match the expected schema. "
                    f"Details: {e}"
                ) from e
            except Exception as exc:
                # Transient errors (network, rate limits) - retry with backoff
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

        May raise UsageLimitExceeded or UnexpectedModelBehavior from pydantic-ai
        if the model fails to produce valid output.

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

        # Add explicit instruction for function calling with local models
        # Local models often ignore the function name and choose their own
        # We explicitly tell them to use "final_result"
        system_prompt += (
            "\n\nIMPORTANT: When returning structured output via function calling, "
            "you MUST use the function named 'final_result'. "
            "Do not create your own function names."
        )

        user_prompt = self._composer.render_user_prompt(
            self._profile,
            self._template_context,
        )

        # Get tools for this agent
        tool_callables = self._tool_registry.get_tool_callables(
            self._profile.tools.allowed
        )

        # Detect provider from base_url
        base_url = self._config.base_url
        is_openrouter = "openrouter.ai" in base_url

        # Create pydantic-ai provider and model
        if is_openrouter:
            provider = OpenRouterProvider(api_key=self._config.api_key)
        else:
            provider = OpenAIProvider(
                base_url=base_url,
                api_key=self._config.api_key,
            )
        model = OpenAIChatModel(self._config.model_id, provider=provider)

        model_settings: OpenAIChatModelSettings = {
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
            "timeout": self._config.timeout_s,
        }

        # Resolve output mode - auto-detect based on provider if "auto"
        output_mode = self._config.output_mode
        if output_mode == "auto":
            # OpenRouter doesn't support tool_choice:required, use prompted mode
            # All other providers use tool mode for structured output
            output_mode = "prompted" if is_openrouter else "tool"

        # Configure output type based on resolved output mode
        if output_mode == "prompted":
            output_type = PromptedOutput(self._output_type)
        else:
            # Tool-based output (default pydantic-ai behavior)
            output_type = self._output_type

        # Create agent with structured output
        # Note: type ignore needed due to pydantic-ai typing limitations with generics
        agent: Agent[None, OutputT] = Agent(  # type: ignore[assignment]
            model=model,
            instructions=system_prompt,
            output_type=output_type,
            tools=tool_callables,
            output_retries=self._config.max_output_retries,
        )

        # Note: We rely on pydantic-ai's built-in validation with output_retries
        # Custom output validators can cause extra validation failures
        # The combination of extra="ignore" and output_retries=3 provides
        # the best balance of strictness and reliability

        # Set usage limits to prevent infinite loops
        # pydantic-ai default is 50 requests which can burn through tokens
        usage_limits = UsageLimits(
            request_limit=self._config.max_requests_per_run,
        )

        result = await agent.run(
            user_prompt,
            model_settings=model_settings,
            usage_limits=usage_limits,
        )
        return result.output
