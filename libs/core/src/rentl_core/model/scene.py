"""Data models for scene metadata records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SceneAnnotations(BaseModel):
    """Combined human/agent metadata for a scene."""

    model_config = ConfigDict(extra="allow")

    notes: str | None = Field(
        default=None,
        description="Free-form notes provided by supervisors or agents.",
        examples=["Establishes Aya and MC dynamic"],
    )
    tags: list[str] = Field(
        default_factory=list, description="Quick tags describing the scene.", examples=[["intro", "school"]]
    )
    summary: str | None = Field(
        default=None, description="Scene summary produced by subagents.", examples=["MC meets Aya on the rooftop."]
    )
    primary_characters: list[str] = Field(
        default_factory=list, description="Characters identified in the scene.", examples=[["mc", "aya"]]
    )
    locations: list[str] = Field(
        default_factory=list, description="Locations identified in the scene.", examples=[["school_rooftop"]]
    )


class SceneMetadata(BaseModel):
    """Metadata entry for a scene (from scenes.jsonl)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique scene identifier.", examples=["scene01"])
    title: str | None = Field(
        default=None, description="Optional human-readable scene title.", examples=["Prologue: Rooftop"]
    )
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
