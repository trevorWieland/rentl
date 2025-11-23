"""Data models for route metadata records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RouteMetadata(BaseModel):
    """Metadata entry for a route (from routes.jsonl)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique route identifier.", examples=["common"])
    name: str = Field(..., description="Human-readable route name.", examples=["Common Route"])
    name_origin: str | None = Field(default=None, description="Provenance for name field.", examples=["human"])
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
    synopsis_origin: str | None = Field(
        default=None, description="Provenance for synopsis field.", examples=["agent:route_detailer:2024-11-22"]
    )
    primary_characters: list[str] = Field(
        default_factory=list, description="Key characters associated with the route.", examples=[["mc", "aya"]]
    )
    primary_characters_origin: str | None = Field(
        default=None,
        description="Provenance for primary_characters field.",
        examples=["agent:route_detailer:2024-11-22"],
    )

    @model_validator(mode="after")
    def validate_provenance(self) -> RouteMetadata:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            RouteMetadata: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.name is not None and self.name_origin is None:
            msg = "name_origin is required when name is set"
            raise ValueError(msg)
        if self.synopsis is not None and self.synopsis_origin is None:
            msg = "synopsis_origin is required when synopsis is set"
            raise ValueError(msg)
        if len(self.primary_characters) > 0 and self.primary_characters_origin is None:
            msg = "primary_characters_origin is required when primary_characters is non-empty"
            raise ValueError(msg)
        return self
