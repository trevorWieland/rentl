"""Input and output data shapes for ingest and export."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    FileFormat,
    JsonValue,
    LineId,
    SceneId,
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


class SourceLine(BaseSchema):
    """Single source line extracted during ingest."""

    line_id: LineId = Field(..., description="Unique line identifier")
    scene_id: SceneId | None = Field(None, description="Scene identifier if available")
    speaker: str | None = Field(None, description="Speaker label if available")
    text: str = Field(..., min_length=1, description="Source text content")
    metadata: dict[str, JsonValue] | None = Field(
        None, description="Additional structured metadata"
    )


class TranslatedLine(BaseSchema):
    """Translated line produced by the translate or edit phase."""

    line_id: LineId = Field(..., description="Unique line identifier")
    source_text: str | None = Field(
        None, description="Original source text for reference"
    )
    text: str = Field(..., min_length=1, description="Translated text content")
    metadata: dict[str, JsonValue] | None = Field(
        None, description="Additional structured metadata"
    )
