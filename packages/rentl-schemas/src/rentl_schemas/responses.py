"""API response envelope schemas for CLI output."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import RequestId, Timestamp


class MetaInfo(BaseSchema):
    """Metadata for API responses."""

    timestamp: Timestamp = Field(..., description="ISO-8601 response timestamp")
    request_id: RequestId | None = Field(
        None, description="Optional request identifier"
    )


class ErrorDetails(BaseSchema):
    """Detailed error context for responses."""

    field: str | None = Field(None, description="Field name if applicable")
    provided: str | None = Field(None, description="Provided value")
    valid_options: list[str] | None = Field(
        None, description="Valid options if applicable"
    )


class ErrorResponse(BaseSchema):
    """Error information in response."""

    code: str = Field(..., min_length=1, description="Error code")
    message: str = Field(..., min_length=1, description="Error message")
    details: ErrorDetails | None = Field(None, description="Optional error details")


class ApiResponse[ResponseData](BaseSchema):
    """Generic API response envelope."""

    data: ResponseData | None = Field(
        None, description="Success payload, null on error"
    )
    error: ErrorResponse | None = Field(
        None, description="Error information, null on success"
    )
    meta: MetaInfo = Field(..., description="Response metadata")
