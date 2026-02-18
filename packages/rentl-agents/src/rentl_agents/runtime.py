"""Profile-driven agent runtime.

This module provides the generic agent runtime that executes agents
defined by TOML profiles.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Literal, TypeVar
from uuid import UUID, uuid7

from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.tools import RunContext, ToolDefinition
from pydantic_ai.usage import RunUsage, UsageLimits

from rentl_agents.layers import PromptComposer, PromptLayerRegistry
from rentl_agents.providers import (
    ProviderCapabilities,
    assert_tool_compatibility,
    build_provider_error_message,
    detect_provider,
)
from rentl_agents.templates import TemplateContext
from rentl_agents.tools.registry import ToolRegistry
from rentl_core import AgentTelemetryEmitter
from rentl_core.ports.orchestrator import PhaseAgentProtocol
from rentl_llm.provider_factory import create_model
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import OpenRouterProviderRoutingConfig
from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import PhaseName, RunId
from rentl_schemas.progress import AgentStatus, AgentTelemetry, AgentUsageTotals

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT_co = TypeVar("OutputT_co", bound=BaseSchema, covariant=True)

DEFAULT_MAX_OUTPUT_TOKENS = 4096


class ProfileAgentConfig(BaseSchema):
    """Configuration for profile-driven agent execution.

    Contains the runtime settings needed to execute an agent.
    """

    api_key: str = Field(..., description="API key for the model provider")
    base_url: str = Field(
        "https://api.openai.com/v1",
        description="Base URL for the model provider API",
    )
    model_id: str = Field(
        ..., description="Model identifier (e.g. 'gpt-5-nano', 'qwen/qwen3-30b-a3b')"
    )
    temperature: float = Field(0.7, description="Sampling temperature for generation")
    top_p: float = Field(1.0, description="Nucleus sampling probability cutoff")
    timeout_s: float = Field(
        180.0, description="Request timeout in seconds per API call"
    )
    max_output_tokens: int | None = Field(
        None, description="Maximum tokens in model output (defaults to 4096 if None)"
    )
    max_retries: int = Field(
        2,
        description="Retries for transient errors only (network, rate limits)",
    )
    retry_base_delay: float = Field(
        2.0, description="Base delay in seconds for exponential backoff between retries"
    )
    openrouter_provider: OpenRouterProviderRoutingConfig | None = Field(
        None, description="OpenRouter-specific provider routing configuration"
    )
    max_requests_per_run: int = Field(
        30,
        description=(
            "Max API requests per single run, including output validation retries"
        ),
    )
    max_output_retries: int = Field(
        10,
        description=(
            "Output validation retries where pydantic-ai provides feedback to model"
        ),
    )
    end_strategy: Literal["early", "exhaustive"] = Field(
        "early",
        description="Strategy for handling tool calls after an output tool is found",
    )
    required_tool_calls: list[str] | None = Field(
        None,
        description="Tool names that must be called before output tools are allowed",
    )


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
        provider = detect_provider(self._config.base_url)
        provider_detected = _build_provider_detected(provider)
        endpoint_type = _build_endpoint_type(provider)
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
                    provider_detected=provider_detected,
                    endpoint_type=endpoint_type,
                    tool_calls_observed=None,
                    required_tools_satisfied=None,
                    message="Agent started",
                ),
                timestamp=started_at,
            )

        max_attempts = self._config.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            try:
                output, usage = await self._execute(payload)
                tool_calls_observed, required_tools_satisfied = (
                    _build_tool_reliability_markers(
                        usage=usage,
                        required_tool_calls=self._config.required_tool_calls,
                    )
                )
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
                            provider_detected=provider_detected,
                            endpoint_type=endpoint_type,
                            tool_calls_observed=tool_calls_observed,
                            required_tools_satisfied=required_tools_satisfied,
                            message="Agent completed",
                        ),
                        timestamp=completed_at,
                    )
                return output
            except UsageLimitExceeded as e:
                _, required_tools_satisfied = _build_tool_reliability_markers(
                    usage=None,
                    required_tool_calls=self._config.required_tool_calls,
                )
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
                            provider_detected=provider_detected,
                            endpoint_type=endpoint_type,
                            tool_calls_observed=None,
                            required_tools_satisfied=required_tools_satisfied,
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
                    f"Try a more capable model (e.g., gpt-5-nano, qwen/qwen3-30b-a3b). "
                    f"Details: {e}"
                ) from e
            except UnexpectedModelBehavior as e:
                _, required_tools_satisfied = _build_tool_reliability_markers(
                    usage=None,
                    required_tool_calls=self._config.required_tool_calls,
                )
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
                            provider_detected=provider_detected,
                            endpoint_type=endpoint_type,
                            tool_calls_observed=None,
                            required_tools_satisfied=required_tools_satisfied,
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
                                provider_detected=provider_detected,
                                endpoint_type=endpoint_type,
                                tool_calls_observed=None,
                                required_tools_satisfied=None,
                                message=f"Retrying after error: {exc}",
                            ),
                            timestamp=_now_timestamp(),
                        )
                    delay = self._config.retry_base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
                completed_at = _now_timestamp()
                _, required_tools_satisfied = _build_tool_reliability_markers(
                    usage=None,
                    required_tool_calls=self._config.required_tool_calls,
                )
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
                            provider_detected=provider_detected,
                            endpoint_type=endpoint_type,
                            tool_calls_observed=None,
                            required_tools_satisfied=required_tools_satisfied,
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

        Raises:
            RuntimeError: If provider is incompatible with tool-only runtime
                requirements.
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

        # Detect provider and enforce tool-only compatibility
        base_url = self._config.base_url
        try:
            assert_tool_compatibility(base_url)
        except ValueError as e:
            error_msg = build_provider_error_message(
                "tool_incompatible",
                base_url,
            )
            raise RuntimeError(error_msg) from e

        # Create provider/model via centralized factory
        max_output_tokens = self._config.max_output_tokens
        if max_output_tokens is None:
            max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        model, model_settings = create_model(
            base_url=base_url,
            api_key=self._config.api_key,
            model_id=self._config.model_id,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            timeout_s=self._config.timeout_s,
            max_output_tokens=max_output_tokens,
            openrouter_provider=self._config.openrouter_provider,
        )

        prepare_output_tools = None
        end_strategy: Literal["early", "exhaustive"] = self._config.end_strategy
        if self._config.required_tool_calls:
            required_tools = set(self._config.required_tool_calls)
            end_strategy = "exhaustive"

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
            output_type=self._output_type,
            tools=tool_callables,
            output_retries=self._config.max_output_retries,
            end_strategy=end_strategy,
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


def _build_provider_detected(provider: ProviderCapabilities) -> str:
    if provider.is_openrouter:
        return "openrouter"
    if provider.name == "OpenAI":
        return "openai"
    if provider.name == "Local/OpenResponses":
        return "local"
    return "openai-compatible"


def _build_endpoint_type(provider: ProviderCapabilities) -> str:
    if provider.name == "Local/OpenResponses":
        return "private"
    return "public"


def _build_tool_reliability_markers(
    *,
    usage: AgentUsageTotals | None,
    required_tool_calls: list[str] | None,
) -> tuple[bool | None, bool | None]:
    tool_calls_observed = usage.tool_calls > 0 if usage is not None else None
    if not required_tool_calls:
        return tool_calls_observed, None
    if usage is None:
        return tool_calls_observed, False
    return tool_calls_observed, usage.tool_calls >= len(required_tool_calls)


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
