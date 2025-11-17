"""Data models for character metadata entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CharacterMetadata(BaseModel):
    """Metadata entry for a character (from characters.jsonl)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique character identifier.", examples=["aya"])
    name_src: str = Field(..., description="Name in the source language.", examples=["綾"])
    name_tgt: str | None = Field(default=None, description="Localized name in the target language.", examples=["Aya"])
    pronouns: str | None = Field(
        default=None, description="Pronoun preferences or notes (free text).", examples=["she/her"]
    )
    notes: str | None = Field(
        default=None,
        description="Additional human-authored notes about the character.",
        examples=["Casual but kind tone"],
    )
