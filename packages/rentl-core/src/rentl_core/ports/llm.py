"""Protocol definitions for LLM runtime adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse


@runtime_checkable
class LlmRuntimeProtocol(Protocol):
    """Protocol for LLM runtime adapters."""

    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        """Execute a prompt against the LLM runtime."""
        raise NotImplementedError
