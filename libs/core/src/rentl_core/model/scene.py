"""Data models for scene metadata records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SceneAnnotations(BaseModel):
    """Combined human/agent metadata for a scene."""

    model_config = ConfigDict(extra="allow")

    notes: str | None = Field(
        default=None,
        description="Free-form notes provided by supervisors or agents.",
        examples=["Establishes Aya and MC dynamic"],
    )
    notes_origin: str | None = Field(default=None, description="Provenance for notes field.", examples=["human"])
    tags: list[str] = Field(
        default_factory=list, description="Quick tags describing the scene.", examples=[["intro", "school"]]
    )
    tags_origin: str | None = Field(default=None, description="Provenance for tags field.", examples=["human"])
    summary: str | None = Field(
        default=None, description="Scene summary produced by subagents.", examples=["MC meets Aya on the rooftop."]
    )
    summary_origin: str | None = Field(
        default=None, description="Provenance for summary field.", examples=["agent:scene_detailer:2024-11-22"]
    )
    primary_characters: list[str] = Field(
        default_factory=list, description="Characters identified in the scene.", examples=[["mc", "aya"]]
    )
    primary_characters_origin: str | None = Field(
        default=None,
        description="Provenance for primary_characters field.",
        examples=["agent:scene_detailer:2024-11-22"],
    )
    locations: list[str] = Field(
        default_factory=list, description="Locations identified in the scene.", examples=[["school_rooftop"]]
    )
    locations_origin: str | None = Field(
        default=None, description="Provenance for locations field.", examples=["agent:scene_detailer:2024-11-22"]
    )

    @model_validator(mode="after")
    def validate_provenance(self) -> SceneAnnotations:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            SceneAnnotations: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.notes is not None and self.notes_origin is None:
            msg = "notes_origin is required when notes is set"
            raise ValueError(msg)
        if len(self.tags) > 0 and self.tags_origin is None:
            msg = "tags_origin is required when tags is non-empty"
            raise ValueError(msg)
        if self.summary is not None and self.summary_origin is None:
            msg = "summary_origin is required when summary is set"
            raise ValueError(msg)
        if len(self.primary_characters) > 0 and self.primary_characters_origin is None:
            msg = "primary_characters_origin is required when primary_characters is non-empty"
            raise ValueError(msg)
        if len(self.locations) > 0 and self.locations_origin is None:
            msg = "locations_origin is required when locations is non-empty"
            raise ValueError(msg)
        return self


class SceneMetadata(BaseModel):
    """Metadata entry for a scene (from scenes.jsonl)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique scene identifier.", examples=["scene01"])
    title: str | None = Field(
        default=None, description="Optional human-readable scene title.", examples=["Prologue: Rooftop"]
    )
    title_origin: str | None = Field(default=None, description="Provenance for title field.", examples=["human"])
    route_ids: list[str] = Field(
        default_factory=list, description="Route IDs that contain this scene.", examples=[["common"]]
    )
    raw_file: str | None = Field(
        default=None, description="Original engine file name for traceability.", examples=["scene01.ks"]
    )
    annotations: SceneAnnotations = Field(
        default_factory=SceneAnnotations,
        description="Combined human- and agent-authored metadata.",
        examples=[
            {
                "notes": "Establishes Aya and MC dynamic",
                "tags": ["intro"],
                "summary": "MC meets Aya",
                "primary_characters": ["mc", "aya"],
            }
        ],
    )

    @model_validator(mode="after")
    def validate_provenance(self) -> SceneMetadata:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            SceneMetadata: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.title is not None and self.title_origin is None:
            msg = "title_origin is required when title is set"
            raise ValueError(msg)
        return self
