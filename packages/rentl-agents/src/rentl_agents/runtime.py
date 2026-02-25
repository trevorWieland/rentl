"""Profile-driven agent runtime.

This module provides the generic agent runtime that executes agents
defined by TOML profiles.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, TypeVar
from uuid import UUID, uuid7

from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
)
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
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    AgentUsageTotals,
    OutputValidationDiagnostic,
)

_logger = logging.getLogger(__name__)

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT_co = TypeVar("OutputT_co", bound=BaseSchema, covariant=True)

DEFAULT_MAX_OUTPUT_TOKENS = 4096
_MAX_DIAGNOSTIC_ENTRIES = 3
_MAX_MODEL_OUTPUT_CHARS = 2000


@dataclass
class _ValidationFailureInfo:
    """Diagnostics extracted from pydantic-ai message history on failure."""

    diagnostics: list[OutputValidationDiagnostic] = field(default_factory=list)
    usage: AgentUsageTotals | None = None


def _extract_validation_diagnostics(
    messages: list[ModelMessage],
) -> list[OutputValidationDiagnostic]:
    """Scan pydantic-ai message history for RetryPromptPart entries.

    Pairs each retry with the preceding ModelResponse tool call args to capture
    what the model produced and why it was rejected.

    Returns:
        Up to the last ``_MAX_DIAGNOSTIC_ENTRIES`` entries, with model output
        truncated to ``_MAX_MODEL_OUTPUT_CHARS``.
    """
    entries: list[OutputValidationDiagnostic] = []
    retry_index = 0
    prev_response: ModelResponse | None = None

    for msg in messages:
        if isinstance(msg, ModelResponse):
            prev_response = msg
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if not isinstance(part, RetryPromptPart):
                    continue
                retry_index += 1

                # Extract model output from the preceding response
                model_output: str | None = None
                if prev_response is not None:
                    # Prefer tool call args (structured output attempt)
                    for resp_part in prev_response.parts:
                        if isinstance(resp_part, ToolCallPart):
                            raw = resp_part.args_as_json_str()
                            model_output = raw[:_MAX_MODEL_OUTPUT_CHARS]
                            break
                    # Fall back to text response
                    if model_output is None and prev_response.parts:
                        text = getattr(prev_response.parts[0], "content", None)
                        if isinstance(text, str):
                            model_output = text[:_MAX_MODEL_OUTPUT_CHARS]

                # Extract validation errors
                validation_errors: list[str] | None = None
                if isinstance(part.content, list):
                    validation_errors = [
                        f"{e.get('loc', '')}: {e.get('msg', '')} [{e.get('type', '')}]"
                        for e in part.content
                    ]
                elif isinstance(part.content, str):
                    validation_errors = [part.content]

                _logger.debug(
                    "Retry %d: errors=%s, model_output=%s",
                    retry_index,
                    validation_errors,
                    model_output,
                )
                entries.append(
                    OutputValidationDiagnostic(
                        retry_index=retry_index,
                        model_output=model_output,
                        validation_errors=validation_errors,
                    )
                )

    return entries[-_MAX_DIAGNOSTIC_ENTRIES:]


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
        5,
        description=(
            "Output validation retries where pydantic-ai provides feedback to model"
        ),
    )
    strict_tools: bool = Field(
        False,
        description="Whether to send strict tool definitions to the provider",
    )
    end_strategy: Literal["early", "exhaustive"] = Field(
        "early",
        description="Strategy for handling tool calls after an output tool is found",
    )
    required_tool_calls: list[str] | None = Field(
        None,
        description="Tool names that must be called before output tools are allowed",
    )
    input_cost_per_mtok: float | None = Field(
        None,
        ge=0,
        description="Input cost per million tokens (USD)",
    )
    output_cost_per_mtok: float | None = Field(
        None,
        ge=0,
        description="Output cost per million tokens (USD)",
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
            UsageLimitExceeded: If the model hits the request limit.
            UnexpectedModelBehavior: If the model produces invalid output.
            RuntimeError: If execution fails after all retries on transient errors.
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
                            cost_usd=usage.cost_usd if usage else None,
                            message="Agent completed",
                        ),
                        timestamp=completed_at,
                    )
                return output
            except UsageLimitExceeded as e:
                failure_info: _ValidationFailureInfo | None = getattr(
                    e, "_validation_failure_info", None
                )
                failure_usage = failure_info.usage if failure_info else None
                failure_diagnostics = (
                    failure_info.diagnostics if failure_info else None
                ) or None
                _, required_tools_satisfied = _build_tool_reliability_markers(
                    usage=failure_usage,
                    required_tool_calls=self._config.required_tool_calls,
                )
                if failure_diagnostics:
                    last_diag = failure_diagnostics[-1]
                    _logger.debug(
                        "Agent %s hit request limit (attempt %d/%d): "
                        "last retry_index=%d, validation_errors=%s, "
                        "model_output=%.200s",
                        self.name,
                        attempt,
                        max_attempts,
                        last_diag.retry_index,
                        last_diag.validation_errors,
                        last_diag.model_output,
                    )
                if required_tools_satisfied is False:
                    _logger.debug(
                        "Agent %s: required tools not called — expected %s",
                        self.name,
                        self._config.required_tool_calls,
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
                            usage=failure_usage,
                            provider_detected=provider_detected,
                            endpoint_type=endpoint_type,
                            tool_calls_observed=None,
                            required_tools_satisfied=required_tools_satisfied,
                            diagnostics=failure_diagnostics,
                            cost_usd=failure_usage.cost_usd if failure_usage else None,
                            message=f"Agent hit request limit: {e}",
                        ),
                        timestamp=completed_at,
                    )
                # Model failed to produce valid output within request limit
                # Re-raise so pool layer can decide whether to retry
                raise
            except UnexpectedModelBehavior as e:
                failure_info = getattr(e, "_validation_failure_info", None)
                failure_usage = failure_info.usage if failure_info else None
                failure_diagnostics = (
                    failure_info.diagnostics if failure_info else None
                ) or None
                _, required_tools_satisfied = _build_tool_reliability_markers(
                    usage=failure_usage,
                    required_tool_calls=self._config.required_tool_calls,
                )
                if failure_diagnostics:
                    last_diag = failure_diagnostics[-1]
                    _logger.debug(
                        "Agent %s produced invalid output (attempt %d/%d): "
                        "last retry_index=%d, validation_errors=%s, "
                        "model_output=%.200s",
                        self.name,
                        attempt,
                        max_attempts,
                        last_diag.retry_index,
                        last_diag.validation_errors,
                        last_diag.model_output,
                    )
                if required_tools_satisfied is False:
                    _logger.debug(
                        "Agent %s: required tools not called — expected %s",
                        self.name,
                        self._config.required_tool_calls,
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
                            usage=failure_usage,
                            provider_detected=provider_detected,
                            endpoint_type=endpoint_type,
                            tool_calls_observed=None,
                            required_tools_satisfied=required_tools_satisfied,
                            diagnostics=failure_diagnostics,
                            cost_usd=failure_usage.cost_usd if failure_usage else None,
                            message=f"Agent produced invalid output: {e}",
                        ),
                        timestamp=completed_at,
                    )
                # Model produced invalid output that couldn't be parsed
                # Re-raise so pool layer can decide whether to retry
                raise
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
            UnexpectedModelBehavior: If model output fails validation after
                retries.
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

        if self._config.required_tool_calls:
            tool_names = ", ".join(self._config.required_tool_calls)
            system_prompt += (
                f"\n\nIMPORTANT: The following tools are required and must be called "
                f"during this task: {tool_names}. Your output will be rejected if "
                f"any required tool has not been called. Call them at the appropriate "
                f"point during your work."
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
            strict_tools=self._config.strict_tools,
        )

        prepare_output_tools = None
        end_strategy: Literal["early", "exhaustive"] = self._config.end_strategy
        required_tools: set[str] | None = None
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

        if required_tools is not None:
            required_captured = required_tools  # capture for closure

            @agent.instructions
            def _required_tools_recovery(ctx: RunContext[None]) -> str | None:
                # Only activate when there are retry messages in history
                has_retries = any(
                    isinstance(msg, ModelRequest)
                    and any(isinstance(p, RetryPromptPart) for p in msg.parts)
                    for msg in ctx.messages
                )
                if not has_retries:
                    return None

                called: set[str] = set()
                for msg in ctx.messages:
                    if isinstance(msg, ModelResponse):
                        for part in msg.parts:
                            if (
                                isinstance(part, ToolCallPart)
                                and part.tool_name in required_captured
                            ):
                                called.add(part.tool_name)
                missing = required_captured - called
                if not missing:
                    return None

                tool_list = ", ".join(sorted(missing))
                _logger.info(
                    "Recovery instructions activated: missing tools %s (called: %s)",
                    tool_list,
                    ", ".join(sorted(called)) or "none",
                )
                return (
                    f"RECOVERY: You have not yet called the required tool(s): "
                    f"{tool_list}. You MUST call these tools before you can "
                    f"produce your final output. Call them now."
                )

        # Set usage limits to prevent infinite loops
        # pydantic-ai default is 50 requests which can burn through tokens
        usage_limits = UsageLimits(
            request_limit=self._config.max_requests_per_run,
        )

        async with agent.iter(
            user_prompt,
            model_settings=model_settings,
            usage_limits=usage_limits,
        ) as agent_run:
            try:
                async for _node in agent_run:
                    pass
                result = agent_run.result
                if result is None:
                    raise UnexpectedModelBehavior(
                        "Agent iteration completed without producing a result"
                    )
                usage = _build_usage_totals(
                    agent_run.usage(),
                    input_cost_per_mtok=self._config.input_cost_per_mtok,
                    output_cost_per_mtok=self._config.output_cost_per_mtok,
                )
                return result.output, usage
            except (UnexpectedModelBehavior, UsageLimitExceeded) as e:
                # Extract diagnostics from message history before re-raising
                info = _ValidationFailureInfo()
                try:
                    all_msgs = agent_run.all_messages()
                    info.diagnostics = _extract_validation_diagnostics(all_msgs)
                    info.usage = _build_usage_totals(
                        agent_run.usage(),
                        input_cost_per_mtok=self._config.input_cost_per_mtok,
                        output_cost_per_mtok=self._config.output_cost_per_mtok,
                    )
                except Exception:
                    pass  # Best-effort extraction
                e._validation_failure_info = info  # type: ignore[attr-defined]
                raise


def _build_usage_totals(
    usage: RunUsage | None,
    *,
    input_cost_per_mtok: float | None = None,
    output_cost_per_mtok: float | None = None,
) -> AgentUsageTotals | None:
    if usage is None or not usage.has_values():
        return None
    cost_usd = _compute_cost_usd(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        input_cost_per_mtok=input_cost_per_mtok,
        output_cost_per_mtok=output_cost_per_mtok,
    )
    return AgentUsageTotals(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        cache_read_tokens=usage.cache_read_tokens,
        cache_write_tokens=usage.cache_write_tokens,
        reasoning_tokens=usage.details.get("reasoning_tokens", 0),
        request_count=usage.requests,
        tool_calls=usage.tool_calls,
        cost_usd=cost_usd,
    )


def _compute_cost_usd(
    *,
    input_tokens: int,
    output_tokens: int,
    input_cost_per_mtok: float | None,
    output_cost_per_mtok: float | None,
) -> float | None:
    """Compute USD cost from token counts and per-million-token pricing.

    Returns:
        Cost in USD, or None when pricing config is not available.
    """
    if input_cost_per_mtok is None or output_cost_per_mtok is None:
        return None
    return (
        input_tokens * input_cost_per_mtok + output_tokens * output_cost_per_mtok
    ) / 1_000_000


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
    if value.version != 7:
        raise ValueError("run_id must be a UUIDv7")
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
