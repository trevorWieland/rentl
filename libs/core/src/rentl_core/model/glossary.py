"""Data models for glossary/terminology entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GlossaryEntry(BaseModel):
    """Glossary entry describing canonical terminology."""

    model_config = ConfigDict(extra="allow")

    term_src: str = Field(..., description="Term in the source language.", examples=["先輩"])
    term_tgt: str | None = Field(
        default=None, description="Preferred rendering in the target language.", examples=["senpai"]
    )
    notes: str | None = Field(
        default=None, description="Additional translation guidance.", examples=["Keep as 'senpai'"]
    )
