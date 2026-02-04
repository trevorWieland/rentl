"""OpenAI-compatible runtime adapter powered by pydantic-ai."""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from rentl_core.ports.llm import LlmRuntimeProtocol
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
        provider = OpenAIProvider(
            base_url=request.runtime.endpoint.base_url,
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
        if request.runtime.model.reasoning_effort is not None:
            effort = request.runtime.model.reasoning_effort
            if isinstance(effort, ReasoningEffort):
                model_settings["openai_reasoning_effort"] = effort.value
            else:
                model_settings["openai_reasoning_effort"] = str(effort)
        max_output_tokens = request.runtime.model.max_output_tokens
        if max_output_tokens is None:
            max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        model_settings["max_tokens"] = max_output_tokens
        instructions = request.system_prompt or "Respond with one short sentence."
        agent = Agent(model, instructions=instructions)
        result = await agent.run(request.prompt, model_settings=model_settings)
        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text=str(result.output),
        )
