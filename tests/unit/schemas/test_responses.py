"""Unit tests for API response schemas."""

from rentl_schemas.responses import ApiResponse, ErrorDetails, ErrorResponse, MetaInfo


def test_api_response_with_error() -> None:
    """Ensure error responses serialize with required fields."""
    response = ApiResponse[dict[str, str]](
        data=None,
        error=ErrorResponse(
            code="VAL_001",
            message="Invalid configuration",
            details=ErrorDetails(
                field="model",
                provided="gpt-0",
                valid_options=["gpt-4"],
            ),
        ),
        meta=MetaInfo(timestamp="2026-01-25T12:00:00Z"),
    )

    payload = response.model_dump()
    assert payload["error"]["code"] == "VAL_001"
