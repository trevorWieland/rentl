"""Data models for game-level metadata (game.json)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CharacterSet(StrEnum):
    """Supported character sets for UI constraints."""

    ASCII = "ascii"
    UNICODE = "unicode"
    SHIFT_JIS = "shift_jis"
    EUC_JP = "euc_jp"


class TimelineEntry(BaseModel):
    """Timeline event entry."""

    when: str = Field(..., description="Time reference.", examples=["Day 1", "2 years before"])
    event: str = Field(..., description="Brief event description.", examples=["MC arrives at new school"])


class UIConstraints(BaseModel):
    """UI/formatting constraints for the game."""

    max_line_length: int | None = Field(
        default=None, description="Maximum characters per line, if enforced.", examples=[40]
    )
    allow_word_wrap: bool = Field(default=True, description="Whether word wrap is supported in the engine.")
    charset: CharacterSet | None = Field(default=None, description="Character set restrictions.", examples=["unicode"])


class GameMetadata(BaseModel):
    """Top-level metadata describing the project/game."""

    model_config = ConfigDict(extra="allow")

    title: str = Field(..., description="Project/game title.", examples=["Example VN"])
    title_origin: str | None = Field(default=None, description="Provenance for title field.", examples=["human"])
    title_src: str | None = Field(
        default=None, description="Game title in source language.", examples=["例のビジュアルノベル"]
    )
    title_src_origin: str | None = Field(
        default=None, description="Provenance for title_src field.", examples=["human"]
    )
    title_tgt: str | None = Field(default=None, description="Game title in target language.", examples=["Example VN"])
    title_tgt_origin: str | None = Field(
        default=None, description="Provenance for title_tgt field.", examples=["human"]
    )
    description: str | None = Field(default=None, description="Short description of the project.")
    description_origin: str | None = Field(
        default=None, description="Provenance for description field.", examples=["human"]
    )
    source_lang: str = Field(..., description="Source language code (ISO 639-3).", examples=["jpn"])
    target_lang: str = Field(..., description="Target language code (ISO 639-3).", examples=["eng"])
    genres: list[str] = Field(
        default_factory=list, description="Optional list of genres.", examples=[["romance", "slice_of_life"]]
    )
    genres_origin: str | None = Field(
        default=None, description="Provenance for genres field.", examples=["agent:game_analyzer:2024-11-22"]
    )
    synopsis: str | None = Field(default=None, description="Optional synopsis or plot summary.")
    synopsis_origin: str | None = Field(default=None, description="Provenance for synopsis field.", examples=["human"])
    timeline: list[TimelineEntry] = Field(default_factory=list, description="Optional chronological events.")
    timeline_origin: str | None = Field(default=None, description="Provenance for timeline field.", examples=["human"])
    ui: UIConstraints = Field(default_factory=UIConstraints, description="UI/formatting constraints.")

    @model_validator(mode="after")
    def validate_provenance(self) -> GameMetadata:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            GameMetadata: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.title is not None and self.title_origin is None:
            msg = "title_origin is required when title is set"
            raise ValueError(msg)
        if self.title_src is not None and self.title_src_origin is None:
            msg = "title_src_origin is required when title_src is set"
            raise ValueError(msg)
        if self.title_tgt is not None and self.title_tgt_origin is None:
            msg = "title_tgt_origin is required when title_tgt is set"
            raise ValueError(msg)
        if self.description is not None and self.description_origin is None:
            msg = "description_origin is required when description is set"
            raise ValueError(msg)
        if len(self.genres) > 0 and self.genres_origin is None:
            msg = "genres_origin is required when genres is non-empty"
            raise ValueError(msg)
        if self.synopsis is not None and self.synopsis_origin is None:
            msg = "synopsis_origin is required when synopsis is set"
            raise ValueError(msg)
        if len(self.timeline) > 0 and self.timeline_origin is None:
            msg = "timeline_origin is required when timeline is non-empty"
            raise ValueError(msg)
        return self
