"""Unit tests for BaseSchema behavior."""

from pydantic import Field

from rentl_schemas.base import BaseSchema


class SampleSchema(BaseSchema):
    """Sample schema for BaseSchema validation checks."""

    name: str = Field(..., min_length=1, description="Name")


def test_extra_fields_ignored() -> None:
    """Ensure extra fields are ignored by BaseSchema (not rejected).

    This improves LLM reliability by allowing models to include additional
    context fields without failing validation. Required fields are still validated.
    """
    # Extra fields should be silently dropped
    result = SampleSchema.model_validate({"name": "ok", "extra": "ignored"})
    assert result.name == "ok"
    assert not hasattr(result, "extra")  # Extra field is dropped
