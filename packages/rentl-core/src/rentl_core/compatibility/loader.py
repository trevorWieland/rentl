"""LM Studio model loader for local model verification."""

from __future__ import annotations

import logging

import httpx

_log = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """Raised when LM Studio model loading fails."""


async def load_lm_studio_model(
    *,
    load_endpoint: str,
    model_id: str,
    api_key: str = "",
    timeout_s: float = 120.0,
) -> None:
    """Load a model in LM Studio via its REST API.

    Sends a POST request to the LM Studio model load endpoint to switch
    the active model before running verification.

    Args:
        load_endpoint: LM Studio load API URL (e.g. http://192.168.1.23:1234/api/v1/models/load).
        model_id: Model identifier to load (e.g. google/gemma-3-27b).
        api_key: API key for LM Studio authentication (Bearer token).
        timeout_s: Request timeout in seconds.

    Raises:
        ModelLoadError: If the model load request fails.
    """
    _log.info("Loading model %s via LM Studio at %s", model_id, load_endpoint)
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
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
