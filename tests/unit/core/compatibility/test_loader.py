"""Unit tests for LM Studio model loader."""

from __future__ import annotations

from unittest.mock import AsyncMock, call, patch

import httpx
import pytest

from rentl_core.compatibility.loader import (
    ModelLoadError,
    ModelUnloadError,
    list_lm_studio_models,
    load_lm_studio_model,
    unload_lm_studio_model,
)

_LOAD_URL = "http://192.168.1.23:1234/api/v1/models/load"
_LIST_URL = "http://192.168.1.23:1234/api/v1/models/list"
_UNLOAD_URL = "http://192.168.1.23:1234/api/v1/models/unload"


# ---- helpers ----------------------------------------------------------------


def _mock_client(
    *,
    post_return: httpx.Response | None = None,
    post_side_effect: Exception | None = None,
    get_return: httpx.Response | None = None,
    get_side_effect: Exception | None = None,
) -> AsyncMock:
    """Build a mock httpx.AsyncClient.

    Returns:
        Configured AsyncMock for httpx.AsyncClient.
    """
    client = AsyncMock()
    if post_side_effect:
        client.post = AsyncMock(side_effect=post_side_effect)
    else:
        resp = post_return or _ok_response()
        client.post = AsyncMock(return_value=resp)
    if get_side_effect:
        client.get = AsyncMock(side_effect=get_side_effect)
    else:
        resp = get_return or _ok_response()
        client.get = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def _ok_response(*, json_data: list[dict[str, str]] | None = None) -> AsyncMock:
    """Build a mock 200 response.

    Returns:
        AsyncMock configured as a successful HTTP response.
    """
    resp = AsyncMock()
    resp.status_code = 200
    resp.raise_for_status = lambda: None
    resp.json = lambda: json_data if json_data is not None else []
    return resp


def _error_response(status: int, text: str, method: str, url: str) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        request=httpx.Request(method, url),
        text=text,
    )


# ---- load_lm_studio_model --------------------------------------------------


async def test_load_model_success() -> None:
    """Successful model load sends correct payload and returns cleanly."""
    list_resp = _ok_response(json_data=[])
    post_resp = _ok_response()
    client = _mock_client(get_return=list_resp, post_return=post_resp)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
            timeout_s=120.0,
        )

    # Should call POST to load (list GET + load POST)
    client.post.assert_awaited_once_with(
        _LOAD_URL,
        json={"model": "google/gemma-3-27b"},
        headers={},
    )


async def test_load_model_http_status_error() -> None:
    """HTTP error status raises ModelLoadError with status code info."""
    err_resp = _error_response(500, "internal error", "POST", _LOAD_URL)
    # list succeeds (empty), but load POST fails
    list_resp = _ok_response(json_data=[])
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(return_value=list_resp)
    client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=err_resp.request,
            response=err_resp,
        )
    )

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelLoadError, match="HTTP 500"),
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )


async def test_load_model_connection_error() -> None:
    """Connection failure raises ModelLoadError with endpoint info."""
    # list fails → loader proceeds with load → load also fails
    client = _mock_client(
        get_side_effect=httpx.ConnectError("Connection refused"),
        post_side_effect=httpx.ConnectError("Connection refused"),
    )

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelLoadError, match="Failed to reach LM Studio"),
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )


async def test_load_model_skips_when_already_loaded() -> None:
    """Skip loading if the target model is already active."""
    list_resp = _ok_response(json_data=[{"id": "google/gemma-3-27b"}])
    client = _mock_client(get_return=list_resp)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )

    # Should NOT call POST to load since model is already active
    client.post.assert_not_awaited()


async def test_load_model_unloads_others_when_target_loaded() -> None:
    """Unload stale models when target is already active but others are loaded."""
    list_resp = _ok_response(
        json_data=[{"id": "google/gemma-3-27b"}, {"id": "qwen/qwen3-vl-30b"}],
    )
    unload_resp = _ok_response()
    client = _mock_client(get_return=list_resp, post_return=unload_resp)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )

    # Should POST to unload the other model, not to load
    client.post.assert_awaited_once_with(
        _UNLOAD_URL,
        json={"instance_id": "qwen/qwen3-vl-30b"},
        headers={},
    )


async def test_load_model_unloads_existing_before_loading_new() -> None:
    """Unload existing models before loading a new one."""
    list_resp = _ok_response(json_data=[{"id": "qwen/qwen3-vl-30b"}])
    ok_resp = _ok_response()
    client = _mock_client(get_return=list_resp, post_return=ok_resp)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )

    # Should have unloaded the old model, then loaded the new one
    assert client.post.await_count == 2
    unload_call = client.post.call_args_list[0]
    assert unload_call == call(
        _UNLOAD_URL,
        json={"instance_id": "qwen/qwen3-vl-30b"},
        headers={},
    )
    load_call = client.post.call_args_list[1]
    assert load_call == call(
        _LOAD_URL,
        json={"model": "google/gemma-3-27b"},
        headers={},
    )


async def test_load_model_proceeds_when_list_fails() -> None:
    """Proceed with load when listing models fails."""
    ok_resp = _ok_response()
    # First call (GET list) fails, second call (POST load) succeeds
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "error",
            request=httpx.Request("GET", _LIST_URL),
            response=_error_response(500, "fail", "GET", _LIST_URL),
        )
    )
    client.post = AsyncMock(return_value=ok_resp)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )

    # Should still POST to load
    client.post.assert_awaited_once()


# ---- list_lm_studio_models -------------------------------------------------


async def test_list_models_success() -> None:
    """List returns model IDs from JSON response."""
    resp = _ok_response(
        json_data=[
            {"id": "google/gemma-3-27b"},
            {"id": "qwen/qwen3-vl-30b"},
        ]
    )
    client = _mock_client(get_return=resp)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        result = await list_lm_studio_models(load_endpoint=_LOAD_URL)

    assert result == ["google/gemma-3-27b", "qwen/qwen3-vl-30b"]
    client.get.assert_awaited_once_with(_LIST_URL, headers={})


async def test_list_models_empty() -> None:
    """List returns empty list when no models are loaded."""
    resp = _ok_response(json_data=[])
    client = _mock_client(get_return=resp)

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        result = await list_lm_studio_models(load_endpoint=_LOAD_URL)

    assert result == []


async def test_list_models_http_error() -> None:
    """HTTP error from list endpoint raises ModelLoadError."""
    err_resp = _error_response(500, "internal error", "GET", _LIST_URL)
    client = _mock_client(
        get_side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=err_resp.request,
            response=err_resp,
        )
    )

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelLoadError, match="HTTP 500"),
    ):
        await list_lm_studio_models(load_endpoint=_LOAD_URL)


async def test_list_models_connection_error() -> None:
    """Connection failure from list endpoint raises ModelLoadError."""
    client = _mock_client(get_side_effect=httpx.ConnectError("Connection refused"))

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelLoadError, match="Failed to reach LM Studio"),
    ):
        await list_lm_studio_models(load_endpoint=_LOAD_URL)


# ---- unload_lm_studio_model ------------------------------------------------


async def test_unload_model_success() -> None:
    """Successful model unload sends correct payload."""
    client = _mock_client()

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        await unload_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )

    client.post.assert_awaited_once_with(
        _UNLOAD_URL,
        json={"instance_id": "google/gemma-3-27b"},
        headers={},
    )


async def test_unload_model_http_error() -> None:
    """HTTP error from unload raises ModelUnloadError."""
    err_resp = _error_response(500, "internal error", "POST", _UNLOAD_URL)
    client = _mock_client(
        post_side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=err_resp.request,
            response=err_resp,
        )
    )

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelUnloadError, match="HTTP 500"),
    ):
        await unload_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )


async def test_unload_model_connection_error() -> None:
    """Connection failure from unload raises ModelUnloadError."""
    client = _mock_client(post_side_effect=httpx.ConnectError("Connection refused"))

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelUnloadError, match="Failed to reach LM Studio"),
    ):
        await unload_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )


async def test_load_model_fails_fast_when_stale_unload_fails() -> None:
    """Unload failure for stale model (target already loaded) raises ModelLoadError."""
    list_resp = _ok_response(
        json_data=[{"id": "google/gemma-3-27b"}, {"id": "qwen/qwen3-vl-30b"}],
    )
    # Build a client where GET (list) succeeds but POST (unload) fails
    err_resp = _error_response(500, "unload failed", "POST", _UNLOAD_URL)
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(return_value=list_resp)
    client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=err_resp.request,
            response=err_resp,
        )
    )

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelLoadError, match="single-model residency"),
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )


async def test_load_model_fails_fast_when_pre_load_unload_fails() -> None:
    """Unload failure before loading new model raises ModelLoadError."""
    list_resp = _ok_response(json_data=[{"id": "qwen/qwen3-vl-30b"}])
    # Build a client where GET (list) succeeds but POST (unload) fails
    err_resp = _error_response(500, "unload failed", "POST", _UNLOAD_URL)
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(return_value=list_resp)
    client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=err_resp.request,
            response=err_resp,
        )
    )

    with (
        patch("rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client),
        pytest.raises(ModelLoadError, match="single-model residency"),
    ):
        await load_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
        )


async def test_unload_model_sends_auth_header() -> None:
    """Auth header is sent when api_key is provided."""
    client = _mock_client()

    with patch(
        "rentl_core.compatibility.loader.httpx.AsyncClient", return_value=client
    ):
        await unload_lm_studio_model(
            load_endpoint=_LOAD_URL,
            model_id="google/gemma-3-27b",
            api_key="secret",
        )

    client.post.assert_awaited_once_with(
        _UNLOAD_URL,
        json={"instance_id": "google/gemma-3-27b"},
        headers={"Authorization": "Bearer secret"},
    )
