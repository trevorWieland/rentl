"""Data models for game-level metadata (game.json)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CharacterSet(StrEnum):
    """Supported character sets for UI constraints."""

    ASCII = "ascii"
    UNICODE = "unicode"
    SHIFT_JIS = "shift_jis"
    EUC_JP = "euc_jp"


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
    description: str | None = Field(default=None, description="Short description of the project.")
    source_lang: str = Field(..., description="Source language code (ISO 639-3).", examples=["jpn"])
    target_lang: str = Field(..., description="Target language code (ISO 639-3).", examples=["eng"])
    genres: list[str] = Field(
        default_factory=list, description="Optional list of genres.", examples=[["romance", "slice_of_life"]]
    )
    synopsis: str | None = Field(default=None, description="Optional synopsis or plot summary.")
    timeline: list[str] = Field(default_factory=list, description="Optional chronological notes or events.")
    ui: UIConstraints = Field(default_factory=UIConstraints, description="UI/formatting constraints.")
