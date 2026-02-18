"""OpenAI-compatible runtime adapter powered by pydantic-ai."""

from __future__ import annotations

from pydantic_ai import Agent

from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_llm.provider_factory import create_model
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse

DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_OUTPUT_RETRIES = 3


class OpenAICompatibleRuntime(LlmRuntimeProtocol):
    """OpenAI-compatible runtime adapter for BYOK endpoints."""

    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        """Execute a prompt using the OpenAI-compatible endpoint.

        Returns:
            LlmPromptResponse: Model output payload.
        """
        max_output_tokens = request.runtime.model.max_output_tokens
        if max_output_tokens is None:
            max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        instructions = request.system_prompt or "Respond with one short sentence."

        model, model_settings = create_model(
            base_url=request.runtime.endpoint.base_url,
            api_key=api_key,
            model_id=request.runtime.model.model_id,
            temperature=request.runtime.model.temperature,
            top_p=request.runtime.model.top_p,
            timeout_s=request.runtime.endpoint.timeout_s,
            max_output_tokens=max_output_tokens,
            presence_penalty=request.runtime.model.presence_penalty,
            frequency_penalty=request.runtime.model.frequency_penalty,
            reasoning_effort=request.runtime.model.reasoning_effort,
            openrouter_provider=request.runtime.endpoint.openrouter_provider,
        )

        # Use structured output if result_schema is provided
        if request.result_schema is not None:
            agent = Agent(
                model,
                output_type=request.result_schema,
                instructions=instructions,
                output_retries=DEFAULT_OUTPUT_RETRIES,
            )
            result = await agent.run(
                request.prompt,
                model_settings=model_settings,
            )
            return LlmPromptResponse(
                model_id=request.runtime.model.model_id,
                output_text=str(result.output),
                structured_output=result.output,  # type: ignore[arg-type]
            )

        agent = Agent(model, instructions=instructions)
        result = await agent.run(
            request.prompt,
            model_settings=model_settings,
        )
        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text=str(result.output),
        )
