"""Data models for location metadata entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocationMetadata(BaseModel):
    """Location entry describing recurring places."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique location identifier.", examples=["school_rooftop"])
    name_src: str = Field(..., description="Location name in the source language.", examples=["屋上"])
    name_src_origin: str | None = Field(default=None, description="Provenance for name_src field.", examples=["human"])
    name_tgt: str | None = Field(default=None, description="Localized location name.", examples=["Rooftop"])
    name_tgt_origin: str | None = Field(default=None, description="Provenance for name_tgt field.", examples=["human"])
    description: str | None = Field(
        default=None, description="Optional description or notes.", examples=["School rooftop overlooking city"]
    )
    description_origin: str | None = Field(
        default=None, description="Provenance for description field.", examples=["agent:location_detailer:2024-11-22"]
    )

    @model_validator(mode="after")
    def validate_provenance(self) -> LocationMetadata:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            LocationMetadata: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.name_src is not None and self.name_src_origin is None:
            msg = "name_src_origin is required when name_src is set"
            raise ValueError(msg)
        if self.name_tgt is not None and self.name_tgt_origin is None:
            msg = "name_tgt_origin is required when name_tgt is set"
            raise ValueError(msg)
        if self.description is not None and self.description_origin is None:
            msg = "description_origin is required when description is set"
            raise ValueError(msg)
        return self
