"""Data models for character metadata entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CharacterMetadata(BaseModel):
    """Metadata entry for a character (from characters.jsonl)."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique character identifier.", examples=["aya"])
    name_src: str = Field(..., description="Name in the source language.", examples=["綾"])
    name_src_origin: str | None = Field(default=None, description="Provenance for name_src field.", examples=["human"])
    name_tgt: str | None = Field(default=None, description="Localized name in the target language.", examples=["Aya"])
    name_tgt_origin: str | None = Field(default=None, description="Provenance for name_tgt field.", examples=["human"])
    pronouns: str | None = Field(
        default=None, description="Pronoun preferences or notes (free text).", examples=["she/her"]
    )
    pronouns_origin: str | None = Field(default=None, description="Provenance for pronouns field.", examples=["human"])
    notes: str | None = Field(
        default=None,
        description="Additional human-authored notes about the character.",
        examples=["Casual but kind tone"],
    )
    notes_origin: str | None = Field(
        default=None, description="Provenance for notes field.", examples=["agent:character_detailer:2024-11-22"]
    )

    @model_validator(mode="after")
    def validate_provenance(self) -> CharacterMetadata:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            CharacterMetadata: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.name_src is not None and self.name_src_origin is None:
            msg = "name_src_origin is required when name_src is set"
            raise ValueError(msg)
        if self.name_tgt is not None and self.name_tgt_origin is None:
            msg = "name_tgt_origin is required when name_tgt is set"
            raise ValueError(msg)
        if self.pronouns is not None and self.pronouns_origin is None:
            msg = "pronouns_origin is required when pronouns is set"
            raise ValueError(msg)
        if self.notes is not None and self.notes_origin is None:
            msg = "notes_origin is required when notes is set"
            raise ValueError(msg)
        return self
