"""Base schema configuration for rentl Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with strict validation defaults."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        validate_default=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        strict=True,
    )
