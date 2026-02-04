"""Unit tests for phase input and output schemas."""

from uuid import UUID

from rentl_schemas.io import TranslatedLine
from rentl_schemas.phases import (
    PretranslationAnnotation,
    PretranslationPhaseOutput,
    TranslatePhaseOutput,
)
from rentl_schemas.primitives import AnnotationId, PhaseName, RunId

RUN_ID: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
ANNOTATION_ID: AnnotationId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b1")


def test_translate_output_accepts_required_fields() -> None:
    """Ensure translate output accepts required fields only."""
    output = TranslatePhaseOutput(
        run_id=RUN_ID,
        phase=PhaseName.TRANSLATE,
        target_language="ja",
        translated_lines=[
            TranslatedLine(line_id="line_01", source_text="hi", text="hola")
        ],
    )

    assert output.phase == PhaseName.TRANSLATE


def test_pretranslation_output_accepts_annotations() -> None:
    """Ensure pretranslation output carries annotations and term candidates."""
    annotation = PretranslationAnnotation(
        annotation_id=ANNOTATION_ID,
        line_id="line_01",
        annotation_type="idiom",
        value="Break a leg",
        notes="Idiomatic expression",
        metadata=None,
    )
    output = PretranslationPhaseOutput(
        run_id=RUN_ID,
        phase=PhaseName.PRETRANSLATION,
        annotations=[annotation],
        term_candidates=[],
    )

    assert output.phase == PhaseName.PRETRANSLATION
