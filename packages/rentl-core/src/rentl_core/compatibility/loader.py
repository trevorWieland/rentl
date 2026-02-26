"""LM Studio model loader for local model verification."""

from __future__ import annotations

import logging

import httpx

_log = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """Raised when LM Studio model loading fails."""


class ModelUnloadError(Exception):
    """Raised when LM Studio model unloading fails."""


def _build_headers(api_key: str) -> dict[str, str]:
    """Build authorization headers for LM Studio requests.

    Returns:
        Headers dict, possibly containing Authorization bearer token.
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _derive_api_base(load_endpoint: str) -> str:
    """Derive the LM Studio API base URL from the load endpoint.

    Given ``http://host:port/api/v1/models/load``, returns
    ``http://host:port/api/v1/models``.

    Returns:
        Base URL with the final path segment removed.
    """
    return load_endpoint.rsplit("/", 1)[0]


async def list_lm_studio_models(
    *,
    load_endpoint: str,
    api_key: str = "",
    timeout_s: float = 30.0,
) -> list[str]:
    """List currently loaded models in LM Studio.

    Uses the v1 REST API ``GET /api/v1/models`` endpoint, which returns all
    known models with their ``loaded_instances``.  A model is considered
    loaded if its ``loaded_instances`` array is non-empty.

    Args:
        load_endpoint: LM Studio load API URL (used to derive the models URL).
        api_key: API key for LM Studio authentication (Bearer token).
        timeout_s: Request timeout in seconds.

    Returns:
        List of model identifiers (``key``) that are currently loaded.

    Raises:
        ModelLoadError: If the list request fails.
    """
    # GET /api/v1/models (the base path, not /api/v1/models/list)
    models_url = _derive_api_base(load_endpoint)
    headers = _build_headers(api_key)
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(models_url, headers=headers)
            response.raise_for_status()
            body: dict[str, list[dict[str, list[dict[str, str]] | str]]] = (
                response.json()
            )
            models = body.get("models", [])
            return [
                str(entry["key"])
                for entry in models
                if "key" in entry and entry.get("loaded_instances")
            ]
    except httpx.HTTPStatusError as exc:
        raise ModelLoadError(
            f"LM Studio returned HTTP {exc.response.status_code} "
            f"when listing models: {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ModelLoadError(
            f"Failed to reach LM Studio at {models_url}: {exc}"
        ) from exc


async def unload_lm_studio_model(
    *,
    load_endpoint: str,
    model_id: str,
    api_key: str = "",
    timeout_s: float = 60.0,
) -> None:
    """Unload a model from LM Studio via its REST API.

    Args:
        load_endpoint: LM Studio load API URL (used to derive the unload URL).
        model_id: Model identifier to unload.
        api_key: API key for LM Studio authentication (Bearer token).
        timeout_s: Request timeout in seconds.

    Raises:
        ModelUnloadError: If the unload request fails.
    """
    base = _derive_api_base(load_endpoint)
    unload_url = f"{base}/unload"
    headers = _build_headers(api_key)
    _log.info("Unloading model %s via LM Studio at %s", model_id, unload_url)
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(
                unload_url,
                json={"instance_id": model_id},
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ModelUnloadError(
            f"LM Studio returned HTTP {exc.response.status_code} "
            f"when unloading model '{model_id}': {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ModelUnloadError(
            f"Failed to reach LM Studio at {unload_url} for model '{model_id}': {exc}"
        ) from exc
    _log.info("Model %s unloaded successfully", model_id)


async def load_lm_studio_model(
    *,
    load_endpoint: str,
    model_id: str,
    api_key: str = "",
    timeout_s: float = 120.0,
) -> None:
    """Load a model in LM Studio via its REST API.

    Resource-aware: queries currently loaded models first, skips loading
    if the target model is already active, and unloads other models before
    loading the new one to prevent GPU memory exhaustion.

    Args:
        load_endpoint: LM Studio load API URL (e.g. http://192.168.1.23:1234/api/v1/models/load).
        model_id: Model identifier to load (e.g. google/gemma-3-27b).
        api_key: API key for LM Studio authentication (Bearer token).
        timeout_s: Request timeout in seconds.

    Raises:
        ModelLoadError: If the model load request fails.
    """
    _log.info("Loading model %s via LM Studio at %s", model_id, load_endpoint)

    # Query currently loaded models — skip load if already active,
    # unload others to free GPU memory before loading.
    try:
        loaded = await list_lm_studio_models(
            load_endpoint=load_endpoint,
            api_key=api_key,
            timeout_s=30.0,
        )
    except ModelLoadError as exc:
        raise ModelLoadError(
            f"Cannot ensure single-model residency: "
            f"failed to list loaded models before loading '{model_id}': {exc}"
        ) from exc

    if model_id in loaded:
        _log.info("Model %s is already loaded — skipping load", model_id)
        # Unload any OTHER loaded models to free memory
        for other_id in loaded:
            if other_id != model_id:
                try:
                    await unload_lm_studio_model(
                        load_endpoint=load_endpoint,
                        model_id=other_id,
                        api_key=api_key,
                        timeout_s=60.0,
                    )
                except ModelUnloadError as exc:
                    raise ModelLoadError(
                        f"Cannot ensure single-model residency: "
                        f"failed to unload stale model '{other_id}' "
                        f"while target '{model_id}' is already loaded: {exc}"
                    ) from exc
        return

    # Unload all currently loaded models before loading the new one
    for loaded_id in loaded:
        try:
            await unload_lm_studio_model(
                load_endpoint=load_endpoint,
                model_id=loaded_id,
                api_key=api_key,
                timeout_s=60.0,
            )
        except ModelUnloadError as exc:
            raise ModelLoadError(
                f"Cannot ensure single-model residency: "
                f"failed to unload model '{loaded_id}' "
                f"before loading '{model_id}': {exc}"
            ) from exc

    headers = _build_headers(api_key)
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(
                load_endpoint,
                json={"model": model_id},
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ModelLoadError(
            f"LM Studio returned HTTP {exc.response.status_code} "
            f"when loading model '{model_id}': {exc.response.text}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ModelLoadError(
            f"Failed to reach LM Studio at {load_endpoint} "
            f"for model '{model_id}': {exc}"
        ) from exc
    _log.info("Model %s loaded successfully", model_id)
