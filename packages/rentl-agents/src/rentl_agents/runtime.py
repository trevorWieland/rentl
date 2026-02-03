"""Profile-driven agent runtime.

This module provides the generic agent runtime that executes agents
defined by TOML profiles.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Literal, TypeVar
from uuid import UUID, uuid7

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.output import OutputSpec, PromptedOutput
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.tools import RunContext, ToolDefinition
from pydantic_ai.usage import RunUsage, UsageLimits

from rentl_agents.layers import PromptComposer, PromptLayerRegistry
from rentl_agents.templates import TemplateContext
from rentl_agents.tools.registry import ToolRegistry
from rentl_core import AgentTelemetryEmitter
from rentl_core.ports.orchestrator import PhaseAgentProtocol
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.base import BaseSchema
from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import PhaseName, RunId
from rentl_schemas.progress import AgentStatus, AgentTelemetry, AgentUsageTotals

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT_co = TypeVar("OutputT_co", bound=BaseSchema, covariant=True)

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
    # Strategy for handling tool calls after an output tool is found
    end_strategy: Literal["early", "exhaustive"] = "early"
    # Optional list of tool names that must be called before output tools are allowed
    required_tool_calls: list[str] | None = None


class ProfileAgent(PhaseAgentProtocol[InputT, OutputT_co]):
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
        output_type: type[OutputT_co],
        layer_registry: PromptLayerRegistry,
        tool_registry: ToolRegistry,
        config: ProfileAgentConfig,
        template_context: TemplateContext | None = None,
        telemetry_emitter: AgentTelemetryEmitter | None = None,
    ) -> None:
        """Initialize the profile agent.

        Args:
            profile: Agent profile configuration.
            output_type: Expected output schema type.
            layer_registry: Prompt layer registry.
            tool_registry: Tool registry.
            config: Runtime configuration.
            template_context: Template context for prompt rendering.
            telemetry_emitter: Optional telemetry emitter for agent status.
        """
        self._profile = profile
        self._output_type = output_type
        self._layer_registry = layer_registry
        self._tool_registry = tool_registry
        self._config = config
        self._template_context = template_context or TemplateContext()
        self._composer = PromptComposer(registry=layer_registry)
        self._telemetry_emitter = telemetry_emitter

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

    async def run(self, payload: InputT) -> OutputT_co:
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
        run_id = _extract_run_id(payload) if self._telemetry_emitter else None
        agent_run_id = _build_agent_run_id(self._profile.meta.name)
        phase = PhaseName(self._profile.meta.phase)
        target_language = getattr(payload, "target_language", None)
        started_at = _now_timestamp()
        if self._telemetry_emitter is not None:
            await _emit_agent_update(
                self._telemetry_emitter,
                run_id=_ensure_run_id(run_id),
                event=ProgressEvent.AGENT_STARTED,
                update=AgentTelemetry(
                    agent_run_id=agent_run_id,
                    agent_name=self._profile.meta.name,
                    phase=phase,
                    target_language=target_language,
                    status=AgentStatus.RUNNING,
                    attempt=1,
                    started_at=started_at,
                    completed_at=None,
                    usage=None,
                    message="Agent started",
                ),
                timestamp=started_at,
            )

        max_attempts = self._config.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            try:
                output, usage = await self._execute(payload)
                completed_at = _now_timestamp()
                if self._telemetry_emitter is not None:
                    await _emit_agent_update(
                        self._telemetry_emitter,
                        run_id=_ensure_run_id(run_id),
                        event=ProgressEvent.AGENT_COMPLETED,
                        update=AgentTelemetry(
                            agent_run_id=agent_run_id,
                            agent_name=self._profile.meta.name,
                            phase=phase,
                            target_language=target_language,
                            status=AgentStatus.COMPLETED,
                            attempt=attempt,
                            started_at=started_at,
                            completed_at=completed_at,
                            usage=usage,
                            message="Agent completed",
                        ),
                        timestamp=completed_at,
                    )
                return output
            except UsageLimitExceeded as e:
                completed_at = _now_timestamp()
                if self._telemetry_emitter is not None:
                    await _emit_agent_update(
                        self._telemetry_emitter,
                        run_id=_ensure_run_id(run_id),
                        event=ProgressEvent.AGENT_FAILED,
                        update=AgentTelemetry(
                            agent_run_id=agent_run_id,
                            agent_name=self._profile.meta.name,
                            phase=phase,
                            target_language=target_language,
                            status=AgentStatus.FAILED,
                            attempt=attempt,
                            started_at=started_at,
                            completed_at=completed_at,
                            usage=None,
                            message=f"Agent hit request limit: {e}",
                        ),
                        timestamp=completed_at,
                    )
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
                completed_at = _now_timestamp()
                if self._telemetry_emitter is not None:
                    await _emit_agent_update(
                        self._telemetry_emitter,
                        run_id=_ensure_run_id(run_id),
                        event=ProgressEvent.AGENT_FAILED,
                        update=AgentTelemetry(
                            agent_run_id=agent_run_id,
                            agent_name=self._profile.meta.name,
                            phase=phase,
                            target_language=target_language,
                            status=AgentStatus.FAILED,
                            attempt=attempt,
                            started_at=started_at,
                            completed_at=completed_at,
                            usage=None,
                            message=f"Agent produced invalid output: {e}",
                        ),
                        timestamp=completed_at,
                    )
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
                if attempt < max_attempts:
                    next_attempt = attempt + 1
                    if self._telemetry_emitter is not None:
                        await _emit_agent_update(
                            self._telemetry_emitter,
                            run_id=_ensure_run_id(run_id),
                            event=ProgressEvent.AGENT_PROGRESS,
                            update=AgentTelemetry(
                                agent_run_id=agent_run_id,
                                agent_name=self._profile.meta.name,
                                phase=phase,
                                target_language=target_language,
                                status=AgentStatus.RUNNING,
                                attempt=next_attempt,
                                started_at=started_at,
                                completed_at=None,
                                usage=None,
                                message=f"Retrying after error: {exc}",
                            ),
                            timestamp=_now_timestamp(),
                        )
                    delay = self._config.retry_base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
                completed_at = _now_timestamp()
                if self._telemetry_emitter is not None:
                    await _emit_agent_update(
                        self._telemetry_emitter,
                        run_id=_ensure_run_id(run_id),
                        event=ProgressEvent.AGENT_FAILED,
                        update=AgentTelemetry(
                            agent_run_id=agent_run_id,
                            agent_name=self._profile.meta.name,
                            phase=phase,
                            target_language=target_language,
                            status=AgentStatus.FAILED,
                            attempt=attempt,
                            started_at=started_at,
                            completed_at=completed_at,
                            usage=None,
                            message=f"Agent execution failed: {exc}",
                        ),
                        timestamp=completed_at,
                    )

        raise RuntimeError(
            f"Agent {self.name} execution failed after {max_attempts} attempts"
        ) from last_error

    async def _execute(
        self, payload: InputT
    ) -> tuple[OutputT_co, AgentUsageTotals | None]:
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
        output_spec: OutputSpec[OutputT_co]
        if output_mode == "prompted":
            output_spec = PromptedOutput(self._output_type)
        else:
            # Tool-based output (default pydantic-ai behavior)
            output_spec = self._output_type

        prepare_output_tools = None
        if self._config.required_tool_calls:
            required_tools = set(self._config.required_tool_calls)

            async def _prepare_output_tools(
                ctx: RunContext[None],
                tool_defs: list[ToolDefinition],
            ) -> list[ToolDefinition]:
                await asyncio.sleep(0)
                remaining = set(required_tools)
                for message in ctx.messages:
                    if isinstance(message, ModelResponse):
                        for part in message.parts:
                            if (
                                isinstance(part, ToolCallPart)
                                and part.tool_name in remaining
                            ):
                                remaining.discard(part.tool_name)
                if remaining:
                    return []
                return tool_defs

            prepare_output_tools = _prepare_output_tools

        agent: Agent[None, OutputT_co] = Agent[None, OutputT_co](
            model=model,
            instructions=system_prompt,
            output_type=output_spec,
            tools=tool_callables,
            output_retries=self._config.max_output_retries,
            end_strategy=self._config.end_strategy,
            prepare_output_tools=prepare_output_tools,
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
        usage = _build_usage_totals(result.usage())
        return result.output, usage


def _build_usage_totals(usage: RunUsage | None) -> AgentUsageTotals | None:
    if usage is None or not usage.has_values():
        return None
    return AgentUsageTotals(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        request_count=usage.requests,
        tool_calls=usage.tool_calls,
    )


def _build_agent_run_id(agent_name: str) -> str:
    return f"{agent_name}_{uuid7().hex}"


def _now_timestamp() -> str:
    timestamp = datetime.now(UTC).isoformat()
    return timestamp.replace("+00:00", "Z")


def _extract_run_id(payload: BaseSchema) -> RunId:
    value = getattr(payload, "run_id", None)
    if value is None:
        raise ValueError("payload is missing run_id")
    if not isinstance(value, UUID):
        raise ValueError("run_id must be a UUID")
    return value


def _ensure_run_id(run_id: RunId | None) -> RunId:
    if run_id is None:
        raise ValueError("run_id is required for telemetry")
    return run_id


async def _emit_agent_update(
    emitter: AgentTelemetryEmitter | None,
    *,
    run_id: RunId,
    event: ProgressEvent,
    update: AgentTelemetry,
    timestamp: str | None = None,
    message: str | None = None,
) -> None:
    if emitter is None:
        return
    await emitter.emit(
        run_id=run_id,
        event=event,
        update=update,
        timestamp=timestamp,
        message=message,
    )
