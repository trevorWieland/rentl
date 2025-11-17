"""Pydantic models for source and translated scene lines."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceLineMeta(BaseModel):
    """Metadata provided with a raw source line."""

    model_config = ConfigDict(extra="allow")

    speaker: str | None = Field(default=None, description="Explicit speaker label, if provided.", examples=["Aya"])
    idioms: list[str] = Field(
        default_factory=list, description="Idioms detected in the source line.", examples=[["先輩"]]
    )
    references: list[str] = Field(
        default_factory=list,
        description="Reference notes detected in the source line.",
        examples=[["Reference to Sailor Moon"]],
    )
    style_notes: list[str] = Field(
        default_factory=list,
        description="Additional style guidance per line.",
        examples=[["Keep any references subtle."]],
    )


class SourceLine(BaseModel):
    """Represents a single raw line from a scene file."""

    id: str = Field(..., description="Stable line identifier.", examples=["scene01_0001"])
    text: str = Field(..., description="Source-language text of the line.", examples=["おはよう。"])
    is_choice: bool = Field(
        default=False, description="Whether this line represents a player choice option.", examples=[False]
    )
    meta: SourceLineMeta = Field(default_factory=SourceLineMeta, description="Source-language metadata annotations.")


class TranslationMeta(BaseModel):
    """Metadata produced during translation/QA passes."""

    model_config = ConfigDict(extra="allow")

    checks: dict[str, tuple[bool, str]] = Field(
        default_factory=dict,
        description="QA check results keyed by check name (pass/fail, note).",
        examples=[
            {"consistency_check": (True, "")},
            {"pronoun_check": (False, "Referenced character is Aya but 'he' was used.")},
        ],
    )


class TranslatedLine(BaseModel):
    """Represents a translated line with source and target text."""

    id: str = Field(..., description="Stable line identifier reused from the source line.", examples=["scene01_0001"])
    text_src: str = Field(
        ..., description="Original source text (copied from the SourceLine).", examples=["おはよう。"]
    )
    text_tgt: str = Field(..., description="Translated target-language text.", examples=["Morning."])
    meta: TranslationMeta = Field(default_factory=TranslationMeta, description="Translation/QA metadata.")

    @classmethod
    def from_source(cls, line: SourceLine, text_tgt: str) -> TranslatedLine:
        """Create a translated line from a raw source line.

        Returns:
            TranslatedLine: New translated line referencing the source id.
        """
        return cls(id=line.id, text_src=line.text, text_tgt=text_tgt)
