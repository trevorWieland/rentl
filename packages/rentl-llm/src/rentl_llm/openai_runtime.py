"""OpenAI-compatible runtime adapter powered by pydantic-ai."""

from __future__ import annotations

from typing import cast

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.models.openrouter import (
    OpenRouterModel,
    OpenRouterModelSettings,
    OpenRouterProviderConfig,
)
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.settings import ModelSettings

from rentl_agents.providers import detect_provider
from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_schemas.config import OpenRouterProviderRoutingConfig
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse
from rentl_schemas.primitives import ReasoningEffort

DEFAULT_MAX_OUTPUT_TOKENS = 4096


class OpenAICompatibleRuntime(LlmRuntimeProtocol):
    """OpenAI-compatible runtime adapter for BYOK endpoints."""

    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        """Execute a prompt using the OpenAI-compatible endpoint.

        Returns:
            LlmPromptResponse: Model output payload.
        """
        base_url = request.runtime.endpoint.base_url
        capabilities = detect_provider(base_url)
        effort = request.runtime.model.reasoning_effort
        effort_value = (
            effort.value
            if isinstance(effort, ReasoningEffort)
            else str(effort)
            if effort is not None
            else None
        )
        max_output_tokens = request.runtime.model.max_output_tokens
        if max_output_tokens is None:
            max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        instructions = request.system_prompt or "Respond with one short sentence."

        if capabilities.is_openrouter:
            provider = OpenRouterProvider(api_key=api_key)
            model = OpenRouterModel(
                request.runtime.model.model_id,
                provider=provider,
            )
            model_settings: OpenRouterModelSettings = {
                "temperature": request.runtime.model.temperature,
                "top_p": request.runtime.model.top_p,
                "presence_penalty": request.runtime.model.presence_penalty,
                "frequency_penalty": request.runtime.model.frequency_penalty,
                "timeout": request.runtime.endpoint.timeout_s,
                "openrouter_provider": _build_openrouter_provider_settings(
                    request.runtime.endpoint.openrouter_provider
                ),
            }
            if effort_value is not None:
                model_settings["openrouter_reasoning"] = {"effort": effort_value}
            model_settings["max_tokens"] = max_output_tokens
            # Use structured output if result_schema is provided
            if request.result_schema is not None:
                agent = Agent(
                    model, output_type=request.result_schema, instructions=instructions
                )
                result = await agent.run(
                    request.prompt,
                    model_settings=cast(ModelSettings, model_settings),
                )
                return LlmPromptResponse(
                    model_id=request.runtime.model.model_id,
                    output_text=str(result.output),
                    structured_output=result.output,  # type: ignore[arg-type]
                )
            else:
                agent = Agent(model, instructions=instructions)
                result = await agent.run(
                    request.prompt,
                    model_settings=cast(ModelSettings, model_settings),
                )
        else:
            provider = OpenAIProvider(
                base_url=base_url,
                api_key=api_key,
            )
            model = OpenAIChatModel(
                request.runtime.model.model_id,
                provider=provider,
            )
            model_settings: OpenAIChatModelSettings = {
                "temperature": request.runtime.model.temperature,
                "top_p": request.runtime.model.top_p,
                "presence_penalty": request.runtime.model.presence_penalty,
                "frequency_penalty": request.runtime.model.frequency_penalty,
                "timeout": request.runtime.endpoint.timeout_s,
            }
            if effort_value is not None:
                model_settings["openai_reasoning_effort"] = effort_value
            model_settings["max_tokens"] = max_output_tokens
            # Use structured output if result_schema is provided
            if request.result_schema is not None:
                agent = Agent(
                    model, output_type=request.result_schema, instructions=instructions
                )
                result = await agent.run(
                    request.prompt,
                    model_settings=cast(ModelSettings, model_settings),
                )
                return LlmPromptResponse(
                    model_id=request.runtime.model.model_id,
                    output_text=str(result.output),
                    structured_output=result.output,  # type: ignore[arg-type]
                )
            else:
                agent = Agent(model, instructions=instructions)
                result = await agent.run(
                    request.prompt,
                    model_settings=cast(ModelSettings, model_settings),
                )
        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text=str(result.output),
        )


def _build_openrouter_provider_settings(
    config: OpenRouterProviderRoutingConfig | None,
) -> OpenRouterProviderConfig:
    resolved = config or OpenRouterProviderRoutingConfig(require_parameters=True)
    payload = resolved.model_dump(mode="python", exclude_none=True)
    return cast(OpenRouterProviderConfig, payload)
