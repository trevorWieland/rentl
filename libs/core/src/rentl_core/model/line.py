"""Pydantic models for source and translated scene lines."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceLineMeta(BaseModel):
    """Metadata provided with a raw source line."""

    model_config = ConfigDict(extra="allow")

    speaker: str | None = Field(default=None, description="Explicit speaker label, if provided.", examples=["Aya"])
    speaker_origin: str | None = Field(default=None, description="Provenance for speaker field.", examples=["human"])
    notes: list[str] = Field(
        default_factory=list,
        description="General metadata notes.",
        examples=[["Branches to Aya route"]],
    )
    notes_origin: str | None = Field(default=None, description="Provenance for notes field.", examples=["human"])
    style_notes: list[str] = Field(
        default_factory=list,
        description="Additional style guidance per line.",
        examples=[["Keep any references subtle."]],
    )
    style_notes_origin: str | None = Field(
        default=None, description="Provenance for style_notes field.", examples=["human"]
    )
    idioms: list[str] = Field(
        default_factory=list, description="Idioms detected in the source line.", examples=[["先輩"]]
    )
    idioms_origin: str | None = Field(
        default=None, description="Provenance for idioms field.", examples=["agent:detect_idioms:2024-11-22"]
    )
    references: list[str] = Field(
        default_factory=list,
        description="Reference notes detected in the source line.",
        examples=[["Reference to Sailor Moon"]],
    )
    references_origin: str | None = Field(
        default=None, description="Provenance for references field.", examples=["agent:detect_references:2024-11-22"]
    )

    @model_validator(mode="after")
    def validate_provenance(self) -> SourceLineMeta:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            SourceLineMeta: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.speaker is not None and self.speaker_origin is None:
            msg = "speaker_origin is required when speaker is set"
            raise ValueError(msg)
        if len(self.notes) > 0 and self.notes_origin is None:
            msg = "notes_origin is required when notes is non-empty"
            raise ValueError(msg)
        if len(self.style_notes) > 0 and self.style_notes_origin is None:
            msg = "style_notes_origin is required when style_notes is non-empty"
            raise ValueError(msg)
        if len(self.idioms) > 0 and self.idioms_origin is None:
            msg = "idioms_origin is required when idioms is non-empty"
            raise ValueError(msg)
        if len(self.references) > 0 and self.references_origin is None:
            msg = "references_origin is required when references is non-empty"
            raise ValueError(msg)
        return self


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
    text_tgt_origin: str | None = Field(
        default=None, description="Provenance for text_tgt field.", examples=["agent:scene_translator:2024-11-22"]
    )
    meta: TranslationMeta = Field(default_factory=TranslationMeta, description="Translation/QA metadata.")

    @model_validator(mode="after")
    def validate_provenance(self) -> TranslatedLine:
        """Ensure that if a field has a value, its _origin is also set.

        Returns:
            TranslatedLine: The validated instance.

        Raises:
            ValueError: If a field has a value but its corresponding _origin field is None.
        """
        if self.text_tgt is not None and self.text_tgt_origin is None:
            msg = "text_tgt_origin is required when text_tgt is set"
            raise ValueError(msg)
        return self

    @classmethod
    def from_source(cls, line: SourceLine, text_tgt: str, text_tgt_origin: str | None = None) -> TranslatedLine:
        """Create a translated line from a raw source line.

        Args:
            line: Source line to translate from.
            text_tgt: Translated target-language text.
            text_tgt_origin: Optional provenance for the translation.

        Returns:
            TranslatedLine: New translated line referencing the source id.
        """
        return cls(id=line.id, text_src=line.text, text_tgt=text_tgt, text_tgt_origin=text_tgt_origin)
