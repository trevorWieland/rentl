"""Data models for route metadata records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RouteMetadata(BaseModel):
    """Metadata entry for a route (from routes.jsonl)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique route identifier.", examples=["common"])
    name: str = Field(..., description="Human-readable route name.", examples=["Common Route"])
    scene_ids: list[str] = Field(
        default_factory=list,
        description="Ordered list of scene IDs belonging to the route.",
        examples=[["scene01", "scene02"]],
    )
    synopsis: str | None = Field(
        default=None,
        description="Optional synopsis or description of the route.",
        examples=["Prologue and shared scenes"],
    )
    primary_characters: list[str] = Field(
        default_factory=list, description="Key characters associated with the route.", examples=[["mc", "aya"]]
    )
