"""Shared utilities for pipeline execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import anyio
from pydantic import BaseModel, Field

# Retryable exception set can be expanded when specific library errors are surfaced.
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    TimeoutError,
    OSError,
)

PIPELINE_FAILURE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    *RETRYABLE_EXCEPTIONS,
    KeyError,
    FileNotFoundError,
)


class PipelineError(BaseModel):
    """Structured error surfaced by a pipeline stage."""

    stage: str = Field(description="Name of the failing stage (e.g., scene_detail, translate_scene).")
    entity_id: str = Field(description="Identifier for the entity being processed (scene/character/etc).")
    error: str = Field(description="Stringified error for display/logging.")


class SkippedItem(BaseModel):
    """Metadata for skipped entities with a human-readable reason."""

    entity_id: str = Field(description="Identifier for the skipped entity.")
    reason: str = Field(description="Reason why the entity was skipped.")


async def run_with_retries[T](
    coro_factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_backoff_seconds: float = 0.5,
    on_retry: Callable[[int, BaseException], None] | None = None,
    retry_exceptions: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
) -> T:
    """Run an async callable with simple exponential backoff retries.

    Args:
        coro_factory: Callable returning the awaitable to execute.
        attempts: Maximum attempts (default 3).
        base_backoff_seconds: Initial backoff delay before exponentiation.
        on_retry: Optional hook called with (attempt_number, exception) before sleeping.
        retry_exceptions: Tuple of exception types that should trigger a retry.

    Returns:
        Result of the callable if it eventually succeeds.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_factory()
        except retry_exceptions as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            if on_retry:
                on_retry(attempt, exc)
            await anyio.sleep(base_backoff_seconds * 2 ** (attempt - 1))

    assert last_exc is not None
    raise last_exc
