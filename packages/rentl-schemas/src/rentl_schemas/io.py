"""Input and output data shapes for ingest and export."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    FileFormat,
    JsonValue,
    LineId,
    RouteId,
    SceneId,
    UntranslatedPolicy,
)


class IngestSource(BaseSchema):
    """Input source definition for ingest into SourceLine records."""

    input_path: str = Field(
        ..., min_length=1, description="Path to the source data file"
    )
    format: FileFormat = Field(..., description="Input file format")


class ExportTarget(BaseSchema):
    """Export target definition for translated output generation."""

    output_path: str = Field(..., min_length=1, description="Path for exported output")
    format: FileFormat = Field(..., description="Output file format")
    untranslated_policy: UntranslatedPolicy = Field(
        UntranslatedPolicy.ERROR,
        description="Policy for handling untranslated lines during export",
    )
    column_order: list[str] | None = Field(
        None, description="Optional CSV column ordering override"
    )
    include_source_text: bool = Field(
        False, description="Include source_text column in CSV output"
    )
    include_scene_id: bool = Field(
        False, description="Include scene_id column in CSV output"
    )
    include_speaker: bool = Field(
        False, description="Include speaker column in CSV output"
    )
    expected_line_count: int | None = Field(
        None, ge=0, description="Optional expected line count for export audit"
    )


class SourceLine(BaseSchema):
    """Single source line extracted during ingest."""

    line_id: LineId = Field(..., description="Unique line identifier")
    route_id: RouteId | None = Field(None, description="Route identifier if available")
    scene_id: SceneId | None = Field(None, description="Scene identifier if available")
    speaker: str | None = Field(None, description="Speaker label if available")
    text: str = Field(..., min_length=1, description="Source text content")
    metadata: dict[str, JsonValue] | None = Field(
        None, description="Additional structured metadata"
    )
    source_columns: list[str] | None = Field(
        None, description="Original CSV column order if known"
    )


class TranslatedLine(BaseSchema):
    """Translated line produced by the translate or edit phase."""

    line_id: LineId = Field(..., description="Unique line identifier")
    route_id: RouteId | None = Field(None, description="Route identifier if available")
    scene_id: SceneId | None = Field(None, description="Scene identifier if available")
    speaker: str | None = Field(None, description="Speaker label if available")
    source_text: str | None = Field(
        None, description="Original source text for reference"
    )
    text: str = Field(..., min_length=1, description="Translated text content")
    metadata: dict[str, JsonValue] | None = Field(
        None, description="Additional structured metadata"
    )
    source_columns: list[str] | None = Field(
        None, description="Original CSV column order if known"
    )
