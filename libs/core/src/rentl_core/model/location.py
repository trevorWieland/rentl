"""Data models for location metadata entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LocationMetadata(BaseModel):
    """Location entry describing recurring places."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique location identifier.", examples=["school_rooftop"])
    name_src: str = Field(..., description="Location name in the source language.", examples=["屋上"])
    name_tgt: str | None = Field(default=None, description="Localized location name.", examples=["Rooftop"])
    description: str | None = Field(
        default=None, description="Optional description or notes.", examples=["School rooftop overlooking city"]
    )
