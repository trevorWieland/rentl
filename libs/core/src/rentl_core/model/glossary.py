"""Data models for glossary/terminology entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GlossaryEntry(BaseModel):
    """Glossary entry describing canonical terminology."""

    model_config = ConfigDict(extra="allow")

    term_src: str = Field(..., description="Term in the source language.", examples=["先輩"])
    term_src_origin: str | None = Field(default=None, description="Provenance for term_src field.", examples=["human"])
    term_tgt: str | None = Field(
        default=None, description="Preferred rendering in the target language.", examples=["senpai"]
    )
    term_tgt_origin: str | None = Field(default=None, description="Provenance for term_tgt field.", examples=["human"])
    notes: str | None = Field(
        default=None, description="Additional translation guidance.", examples=["Keep as 'senpai'"]
    )
    notes_origin: str | None = Field(default=None, description="Provenance for notes field.", examples=["human"])

    @model_validator(mode="after")
    def validate_provenance(self) -> GlossaryEntry:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            GlossaryEntry: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.term_src is not None and self.term_src_origin is None:
            msg = "term_src_origin is required when term_src is set"
            raise ValueError(msg)
        if self.term_tgt is not None and self.term_tgt_origin is None:
            msg = "term_tgt_origin is required when term_tgt is set"
            raise ValueError(msg)
        if self.notes is not None and self.notes_origin is None:
            msg = "notes_origin is required when notes is set"
            raise ValueError(msg)
        return self
