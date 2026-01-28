"""LLM connection planning and validation helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import monotonic

from rentl_core.ports.llm import LlmRuntimeProtocol
from rentl_schemas.config import (
    ModelEndpointConfig,
    ModelSettings,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.llm import (
    LlmConnectionReport,
    LlmConnectionResult,
    LlmConnectionStatus,
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptRequest,
    LlmPromptResponse,
    LlmRuntimeSettings,
)
from rentl_schemas.primitives import PhaseName, ReasoningEffort

_LLM_PHASES = {
    PhaseName.CONTEXT,
    PhaseName.PRETRANSLATION,
    PhaseName.TRANSLATE,
    PhaseName.QA,
    PhaseName.EDIT,
}


@dataclass(frozen=True)
class LlmConnectionTarget:
    """Resolved runtime target for connectivity checks."""

    runtime: LlmRuntimeSettings
    phases: tuple[PhaseName, ...]


def build_connection_plan(
    config: RunConfig,
) -> tuple[list[LlmConnectionTarget], list[LlmEndpointTarget]]:
    """Build resolved connection targets and unused endpoints.

    Args:
        config: Run configuration to resolve endpoints and models.

    Returns:
        tuple[list[LlmConnectionTarget], list[LlmEndpointTarget]]: Targets and
        unused endpoints.
    """
    endpoint_lookup: dict[str, ModelEndpointConfig] = {}
    if config.endpoints is not None:
        endpoint_lookup = {
            endpoint.provider_name: endpoint for endpoint in config.endpoints.endpoints
        }
    used_refs: set[str] = set()
    targets: dict[
        tuple[
            str | None,
            str,
            str,
            float,
            int | None,
            str | None,
            float,
            float,
            float,
            int,
            float,
            float,
        ],
        tuple[LlmRuntimeSettings, list[PhaseName]],
    ] = {}
    for phase in config.pipeline.phases:
        if not phase.enabled:
            continue
        if phase.phase not in _LLM_PHASES:
            continue
        model_settings = phase.model or config.pipeline.default_model
        if model_settings is None:
            continue
        retry = phase.retry or config.retry
        endpoint_target = _resolve_endpoint_target(
            config=config,
            model_settings=model_settings,
            endpoint_lookup=endpoint_lookup,
        )
        if endpoint_target.endpoint_ref is not None:
            used_refs.add(endpoint_target.endpoint_ref)
        llm_model = _map_model_settings(model_settings)
        runtime = LlmRuntimeSettings(
            endpoint=endpoint_target,
            model=llm_model,
            retry=retry,
        )
        key = _target_key(runtime, retry)
        phase_name = PhaseName(phase.phase)
        entry = targets.get(key)
        if entry is None:
            targets[key] = (runtime, [phase_name])
        else:
            entry[1].append(phase_name)
    plan = [
        LlmConnectionTarget(runtime=runtime, phases=tuple(phases))
        for runtime, phases in targets.values()
    ]
    unused = _collect_unused_endpoints(config, used_refs)
    return plan, unused


async def validate_connections(
    runtime: LlmRuntimeProtocol,
    targets: Sequence[LlmConnectionTarget],
    *,
    prompt: str,
    system_prompt: str | None,
    api_key_lookup: Callable[[LlmEndpointTarget], str | None],
    skipped_endpoints: Sequence[LlmEndpointTarget] | None = None,
) -> LlmConnectionReport:
    """Validate connectivity across resolved targets.

    Args:
        runtime: LLM runtime adapter.
        targets: Connection targets to validate.
        prompt: Prompt text to send.
        system_prompt: Optional system prompt.
        api_key_lookup: Function that returns an API key for the endpoint.
        skipped_endpoints: Endpoints without a configured model reference.

    Returns:
        LlmConnectionReport: Connectivity results.
    """
    results: list[LlmConnectionResult] = []
    tasks: list[asyncio.Task[LlmConnectionResult]] = []
    async with asyncio.TaskGroup() as group:
        for target in targets:
            tasks.append(
                group.create_task(
                    _check_target(
                        runtime=runtime,
                        target=target,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        api_key_lookup=api_key_lookup,
                    )
                )
            )
    for task in tasks:
        results.append(task.result())
    for endpoint in skipped_endpoints or []:
        results.append(_build_skipped_result(endpoint))
    return _summarize_results(results)


async def _check_target(
    *,
    runtime: LlmRuntimeProtocol,
    target: LlmConnectionTarget,
    prompt: str,
    system_prompt: str | None,
    api_key_lookup: Callable[[LlmEndpointTarget], str | None],
) -> LlmConnectionResult:
    endpoint = target.runtime.endpoint
    api_key = api_key_lookup(endpoint)
    if not api_key:
        message = f"Missing API key environment variable: {endpoint.api_key_env}"
        return _build_failure_result(
            endpoint=endpoint,
            model_id=target.runtime.model.model_id,
            phases=target.phases,
            attempts=0,
            duration_ms=None,
            error_message=message,
        )
    request = LlmPromptRequest(
        runtime=target.runtime,
        prompt=prompt,
        system_prompt=system_prompt,
    )
    return await _run_with_retry(
        runtime=runtime,
        request=request,
        api_key=api_key,
        phases=target.phases,
    )


async def _run_with_retry(
    *,
    runtime: LlmRuntimeProtocol,
    request: LlmPromptRequest,
    api_key: str,
    phases: tuple[PhaseName, ...],
) -> LlmConnectionResult:
    retry = request.runtime.retry
    max_attempts = retry.max_retries + 1
    attempts = 0
    delay = retry.backoff_s
    start = monotonic()
    last_error: str | None = None
    while attempts < max_attempts:
        attempts += 1
        try:
            response = await runtime.run_prompt(request, api_key=api_key)
        except Exception as exc:
            last_error = _format_error(exc)
            if attempts >= max_attempts:
                break
            await asyncio.sleep(min(delay, retry.max_backoff_s))
            delay = min(delay * 2, retry.max_backoff_s)
        else:
            duration_ms = _duration_ms(start)
            return _build_success_result(
                endpoint=request.runtime.endpoint,
                response=response,
                phases=phases,
                attempts=attempts,
                duration_ms=duration_ms,
            )
    duration_ms = _duration_ms(start)
    return _build_failure_result(
        endpoint=request.runtime.endpoint,
        model_id=request.runtime.model.model_id,
        phases=phases,
        attempts=attempts,
        duration_ms=duration_ms,
        error_message=last_error or "Unknown error",
    )


def _resolve_endpoint_target(
    *,
    config: RunConfig,
    model_settings: ModelSettings,
    endpoint_lookup: dict[str, ModelEndpointConfig],
) -> LlmEndpointTarget:
    endpoint_ref = config.resolve_endpoint_ref(model=model_settings)
    if config.endpoints is None:
        endpoint = config.endpoint
        if endpoint is None:
            raise ValueError("Missing endpoint configuration")
        return _build_endpoint_target(endpoint, endpoint_ref=None)
    if endpoint_ref is None:
        raise ValueError("Endpoint reference resolution failed")
    endpoint = endpoint_lookup.get(endpoint_ref)
    if endpoint is None:
        raise ValueError(f"Unknown endpoint reference: {endpoint_ref}")
    return _build_endpoint_target(endpoint, endpoint_ref=endpoint_ref)


def _build_endpoint_target(
    endpoint: ModelEndpointConfig, *, endpoint_ref: str | None
) -> LlmEndpointTarget:
    return LlmEndpointTarget(
        endpoint_ref=endpoint_ref,
        provider_name=endpoint.provider_name,
        base_url=endpoint.base_url,
        api_key_env=endpoint.api_key_env,
        timeout_s=endpoint.timeout_s,
    )


def _collect_unused_endpoints(
    config: RunConfig,
    used_refs: set[str],
) -> list[LlmEndpointTarget]:
    if config.endpoints is None:
        return []
    unused: list[LlmEndpointTarget] = []
    for endpoint in config.endpoints.endpoints:
        if endpoint.provider_name in used_refs:
            continue
        unused.append(
            _build_endpoint_target(
                endpoint,
                endpoint_ref=endpoint.provider_name,
            )
        )
    return unused


def _map_model_settings(model: ModelSettings) -> LlmModelSettings:
    reasoning_effort = _coerce_reasoning_effort(model.reasoning_effort)
    return LlmModelSettings(
        model_id=model.model_id,
        temperature=model.temperature,
        max_output_tokens=model.max_output_tokens,
        reasoning_effort=reasoning_effort,
        top_p=model.top_p,
        presence_penalty=model.presence_penalty,
        frequency_penalty=model.frequency_penalty,
    )


def _target_key(
    runtime: LlmRuntimeSettings, retry: RetryConfig
) -> tuple[
    str | None,
    str,
    str,
    float,
    int | None,
    str | None,
    float,
    float,
    float,
    int,
    float,
    float,
]:
    model = runtime.model
    endpoint = runtime.endpoint
    return (
        endpoint.endpoint_ref,
        model.model_id,
        endpoint.base_url,
        model.temperature,
        model.max_output_tokens,
        model.reasoning_effort,
        model.top_p,
        model.presence_penalty,
        model.frequency_penalty,
        retry.max_retries,
        retry.backoff_s,
        retry.max_backoff_s,
    )


def _build_success_result(
    *,
    endpoint: LlmEndpointTarget,
    response: LlmPromptResponse,
    phases: tuple[PhaseName, ...],
    attempts: int,
    duration_ms: int,
) -> LlmConnectionResult:
    return LlmConnectionResult(
        endpoint_ref=endpoint.endpoint_ref,
        provider_name=endpoint.provider_name,
        base_url=endpoint.base_url,
        api_key_env=endpoint.api_key_env,
        model_id=response.model_id,
        phases=list(phases) if phases else None,
        status=LlmConnectionStatus.SUCCESS,
        attempts=attempts,
        duration_ms=duration_ms,
        response_text=_truncate_text(response.output_text),
        error_message=None,
    )


def _build_failure_result(
    *,
    endpoint: LlmEndpointTarget,
    model_id: str | None,
    phases: tuple[PhaseName, ...],
    attempts: int,
    duration_ms: int | None,
    error_message: str,
) -> LlmConnectionResult:
    return LlmConnectionResult(
        endpoint_ref=endpoint.endpoint_ref,
        provider_name=endpoint.provider_name,
        base_url=endpoint.base_url,
        api_key_env=endpoint.api_key_env,
        model_id=model_id,
        phases=list(phases) if phases else None,
        status=LlmConnectionStatus.FAILED,
        attempts=attempts,
        duration_ms=duration_ms,
        response_text=None,
        error_message=error_message,
    )


def _build_skipped_result(endpoint: LlmEndpointTarget) -> LlmConnectionResult:
    return LlmConnectionResult(
        endpoint_ref=endpoint.endpoint_ref,
        provider_name=endpoint.provider_name,
        base_url=endpoint.base_url,
        api_key_env=endpoint.api_key_env,
        model_id=None,
        phases=None,
        status=LlmConnectionStatus.SKIPPED,
        attempts=0,
        duration_ms=None,
        response_text=None,
        error_message="No model configured for endpoint",
    )


def _summarize_results(results: Sequence[LlmConnectionResult]) -> LlmConnectionReport:
    success_count = sum(
        1 for result in results if result.status == LlmConnectionStatus.SUCCESS
    )
    failure_count = sum(
        1 for result in results if result.status == LlmConnectionStatus.FAILED
    )
    skipped_count = sum(
        1 for result in results if result.status == LlmConnectionStatus.SKIPPED
    )
    return LlmConnectionReport(
        results=list(results),
        success_count=success_count,
        failure_count=failure_count,
        skipped_count=skipped_count,
    )


def _truncate_text(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _duration_ms(start: float) -> int:
    return int((monotonic() - start) * 1000)


def _format_error(exc: Exception) -> str:
    message = str(exc).strip()
    return message or repr(exc)


def _coerce_reasoning_effort(
    value: ReasoningEffort | str | None,
) -> ReasoningEffort | None:
    if value is None:
        return None
    if isinstance(value, ReasoningEffort):
        return value
    return ReasoningEffort(value)
