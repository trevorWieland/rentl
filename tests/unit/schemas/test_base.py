"""Unit tests for BaseSchema behavior."""

import pytest
from pydantic import Field, ValidationError

from rentl_schemas.base import BaseSchema


class SampleSchema(BaseSchema):
    """Sample schema for BaseSchema validation checks."""

    name: str = Field(..., min_length=1, description="Name")


def test_extra_fields_forbidden() -> None:
    """Ensure extra fields are rejected by BaseSchema."""
    with pytest.raises(ValidationError):
        SampleSchema.model_validate({"name": "ok", "extra": "nope"})
