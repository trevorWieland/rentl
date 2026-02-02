"""Base schema configuration for rentl Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with strict validation defaults.

    Note: extra="ignore" allows LLMs to include additional fields without
    failing validation. This improves reliability with less capable models
    that may add extra context fields. Required fields are still validated.
    """

    model_config = ConfigDict(
        extra="ignore",  # Drop extra fields instead of failing
        validate_assignment=True,
        validate_default=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        strict=True,
    )
