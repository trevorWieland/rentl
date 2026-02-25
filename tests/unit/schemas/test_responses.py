"""Unit tests for API response schemas."""

from uuid import UUID

from rentl_schemas.primitives import PhaseName, RunStatus
from rentl_schemas.responses import (
    ApiResponse,
    ErrorDetails,
    ErrorResponse,
    MetaInfo,
    RunStatusResult,
)


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
            exit_code=11,
        ),
        meta=MetaInfo(timestamp="2026-01-25T12:00:00Z"),
    )

    payload = response.model_dump()
    assert payload["error"]["code"] == "VAL_001"
    assert payload["error"]["exit_code"] == 11


def test_run_status_result_coerces_current_phase_string() -> None:
    """Ensure RunStatusResult coerces current_phase string to PhaseName."""
    result = RunStatusResult(
        run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0"),
        status=RunStatus.RUNNING,
        current_phase="translate",  # type: ignore[arg-type]
        updated_at="2026-01-26T00:00:00Z",
    )
    assert result.current_phase == PhaseName.TRANSLATE
