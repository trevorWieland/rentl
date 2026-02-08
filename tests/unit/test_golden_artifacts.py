"""Unit tests for golden artifact schema validation."""

import json
from pathlib import Path

from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import (
    IdiomAnnotationList,
    SceneSummary,
    StyleGuideReviewList,
    TranslationResultList,
)
from rentl_schemas.qa import LineEdit

# Path to golden artifacts
GOLDEN_DIR = Path(__file__).parent.parent.parent / "samples" / "golden"
ARTIFACTS_DIR = GOLDEN_DIR / "artifacts"


def test_golden_script_validates_as_source_lines() -> None:
    """Verify golden script.jsonl lines validate as SourceLine."""
    script_path = GOLDEN_DIR / "script.jsonl"
    assert script_path.exists(), f"Golden script not found at {script_path}"

    with open(script_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) > 0, "Golden script is empty"

    for line_data in lines:
        source_line = SourceLine.model_validate(line_data)
        assert source_line.line_id
        assert source_line.text


def test_golden_context_validates_as_scene_summaries() -> None:
    """Verify golden context.jsonl validates as SceneSummary records."""
    context_path = ARTIFACTS_DIR / "context.jsonl"
    assert context_path.exists(), f"Golden context not found at {context_path}"

    with open(context_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) > 0, "Golden context is empty"

    for line_data in lines:
        scene_summary = SceneSummary.model_validate(line_data)
        assert scene_summary.scene_id
        assert scene_summary.summary
        assert isinstance(scene_summary.characters, list)


def test_golden_pretranslation_validates_as_idiom_annotations() -> None:
    """Verify golden pretranslation.jsonl validates as IdiomAnnotationList."""
    pretranslation_path = ARTIFACTS_DIR / "pretranslation.jsonl"
    assert pretranslation_path.exists(), (
        f"Golden pretranslation not found at {pretranslation_path}"
    )

    with open(pretranslation_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) > 0, "Golden pretranslation is empty"

    for line_data in lines:
        annotation_list = IdiomAnnotationList.model_validate(line_data)
        assert isinstance(annotation_list.idioms, list)
        for idiom in annotation_list.idioms:
            assert idiom.line_id
            assert idiom.idiom_text
            assert idiom.explanation


def test_golden_translate_validates_as_translation_results() -> None:
    """Verify golden translate.jsonl validates as TranslationResultList."""
    translate_path = ARTIFACTS_DIR / "translate.jsonl"
    assert translate_path.exists(), f"Golden translate not found at {translate_path}"

    with open(translate_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) > 0, "Golden translate is empty"

    for line_data in lines:
        result_list = TranslationResultList.model_validate(line_data)
        assert len(result_list.translations) > 0
        for translation in result_list.translations:
            assert translation.line_id
            assert translation.text


def test_golden_qa_validates_as_style_guide_reviews() -> None:
    """Verify golden qa.jsonl validates as StyleGuideReviewList."""
    qa_path = ARTIFACTS_DIR / "qa.jsonl"
    assert qa_path.exists(), f"Golden QA not found at {qa_path}"

    with open(qa_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) > 0, "Golden QA is empty"

    for line_data in lines:
        review_list = StyleGuideReviewList.model_validate(line_data)
        assert len(review_list.reviews) > 0
        for review in review_list.reviews:
            assert review.line_id
            assert isinstance(review.violations, list)
            for violation in review.violations:
                assert violation.rule_violated
                assert violation.explanation


def test_golden_edit_validates_as_line_edits() -> None:
    """Verify golden edit.jsonl validates as LineEdit records."""
    edit_path = ARTIFACTS_DIR / "edit.jsonl"
    assert edit_path.exists(), f"Golden edit not found at {edit_path}"

    with open(edit_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) > 0, "Golden edit is empty"

    for line_data in lines:
        line_edit = LineEdit.model_validate(line_data)
        assert line_edit.line_id
        assert line_edit.original_text
        assert line_edit.edited_text


def test_golden_export_validates_as_translated_lines() -> None:
    """Verify golden export.jsonl validates as TranslatedLine records."""
    export_path = ARTIFACTS_DIR / "export.jsonl"
    assert export_path.exists(), f"Golden export not found at {export_path}"

    with open(export_path) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) > 0, "Golden export is empty"

    for line_data in lines:
        translated_line = TranslatedLine.model_validate(line_data)
        assert translated_line.line_id
        assert translated_line.text
