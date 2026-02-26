"""Unit tests for LM Studio model loader."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from rentl_core.compatibility.loader import ModelLoadError, load_lm_studio_model


async def test_load_model_success() -> None:
    """Successful model load sends correct payload and returns cleanly."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=mock_client
    ):
        await load_lm_studio_model(
            load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
            model_id="google/gemma-3-27b",
            timeout_s=120.0,
        )

    mock_client.post.assert_awaited_once_with(
        "http://192.168.1.23:1234/api/v1/models/load",
        json={"identifier": "google/gemma-3-27b"},
    )


async def test_load_model_http_status_error() -> None:
    """HTTP error status raises ModelLoadError with status code info."""
    mock_response = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "http://192.168.1.23:1234/api/v1/models/load"),
        text="internal error",
    )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=mock_response.request,
            response=mock_response,
        )
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "rentl_core.compatibility.loader.httpx.AsyncClient",
            return_value=mock_client,
        ),
        pytest.raises(ModelLoadError, match="HTTP 500"),
    ):
        await load_lm_studio_model(
            load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
            model_id="google/gemma-3-27b",
        )


async def test_load_model_connection_error() -> None:
    """Connection failure raises ModelLoadError with endpoint info."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "rentl_core.compatibility.loader.httpx.AsyncClient",
            return_value=mock_client,
        ),
        pytest.raises(ModelLoadError, match="Failed to reach LM Studio"),
    ):
        await load_lm_studio_model(
            load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
            model_id="google/gemma-3-27b",
        )
