"""Unit tests for translate phase utilities."""

from __future__ import annotations

from uuid import uuid7

import pytest

from rentl_agents.translate import (
    chunk_lines,
    format_annotated_lines_for_prompt,
    format_glossary_terms,
    format_lines_for_prompt,
    format_pretranslation_annotations,
    get_scene_summary_for_lines,
    merge_translated_lines,
    translation_result_to_lines,
)
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import (
    GlossaryTerm,
    PretranslationAnnotation,
    SceneSummary,
    TranslationResultLine,
    TranslationResultList,
)


class TestChunkLines:
    """Test cases for chunk_lines function."""

    def test_chunk_single_chunk(self) -> None:
        """Test chunking when all lines fit in one chunk."""
        lines = [
            SourceLine(line_id="line_1", text="Hello"),
            SourceLine(line_id="line_2", text="World"),
        ]

        chunks = chunk_lines(lines, chunk_size=10)

        assert len(chunks) == 1
        assert len(chunks[0]) == 2

    def test_chunk_multiple_chunks(self) -> None:
        """Test chunking into multiple chunks."""
        lines = [SourceLine(line_id=f"line_{i}", text=f"Line {i}") for i in range(10)]

        chunks = chunk_lines(lines, chunk_size=3)

        assert len(chunks) == 4  # 3 + 3 + 3 + 1
        assert len(chunks[0]) == 3
        assert len(chunks[1]) == 3
        assert len(chunks[2]) == 3
        assert len(chunks[3]) == 1

    def test_chunk_exact_division(self) -> None:
        """Test chunking when lines divide evenly."""
        lines = [SourceLine(line_id=f"line_{i}", text=f"Line {i}") for i in range(9)]

        chunks = chunk_lines(lines, chunk_size=3)

        assert len(chunks) == 3
        assert all(len(chunk) == 3 for chunk in chunks)

    def test_chunk_empty_input(self) -> None:
        """Test chunking empty input."""
        chunks = chunk_lines([], chunk_size=10)

        assert chunks == []

    def test_chunk_size_zero_raises(self) -> None:
        """Test that chunk_size=0 raises error."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_lines([], chunk_size=0)

    def test_chunk_size_negative_raises(self) -> None:
        """Test that negative chunk_size raises error."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_lines([], chunk_size=-1)

    def test_chunk_respects_scene_boundaries(self) -> None:
        """Test that lines from same scene stay together when possible."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="B", scene_id="scene_001"),
            SourceLine(line_id="line_3", text="C", scene_id="scene_002"),
            SourceLine(line_id="line_4", text="D", scene_id="scene_002"),
        ]

        # With chunk_size=3, scene_001 (2 lines) + scene_002 (2 lines) = 4 lines
        # Should create: [scene_001: 2 lines] then [scene_002: 2 lines]
        # because adding scene_002 to first chunk would exceed limit
        chunks = chunk_lines(lines, chunk_size=3)

        assert len(chunks) == 2
        # First chunk should be scene_001
        assert all(line.scene_id == "scene_001" for line in chunks[0])
        # Second chunk should be scene_002
        assert all(line.scene_id == "scene_002" for line in chunks[1])

    def test_chunk_combines_small_scenes(self) -> None:
        """Test that small consecutive scenes are combined up to chunk_size."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="B", scene_id="scene_002"),
            SourceLine(line_id="line_3", text="C", scene_id="scene_003"),
        ]

        # With chunk_size=5, all 3 single-line scenes fit in one chunk
        chunks = chunk_lines(lines, chunk_size=5)

        assert len(chunks) == 1
        assert len(chunks[0]) == 3

    def test_chunk_splits_large_scene(self) -> None:
        """Test that a scene larger than chunk_size is split."""
        lines = [
            SourceLine(line_id=f"line_{i}", text=f"L{i}", scene_id="scene_001")
            for i in range(7)
        ]

        # With chunk_size=3, scene with 7 lines becomes: 3 + 3 + 1
        chunks = chunk_lines(lines, chunk_size=3)

        assert len(chunks) == 3
        assert len(chunks[0]) == 3
        assert len(chunks[1]) == 3
        assert len(chunks[2]) == 1

    def test_chunk_handles_none_scene_ids(self) -> None:
        """Test chunking when lines have no scene_id."""
        lines = [
            SourceLine(line_id="line_1", text="A"),
            SourceLine(line_id="line_2", text="B"),
            SourceLine(line_id="line_3", text="C"),
        ]

        # Lines without scene_id are treated as same scene (None)
        chunks = chunk_lines(lines, chunk_size=2)

        assert len(chunks) == 2
        assert len(chunks[0]) == 2
        assert len(chunks[1]) == 1


class TestFormatLinesForPrompt:
    """Test cases for format_lines_for_prompt function."""

    def test_format_with_speakers(self) -> None:
        """Test formatting lines with speakers."""
        lines = [
            SourceLine(
                line_id="line_001",
                text="Hello there!",
                speaker="Alice",
            ),
            SourceLine(
                line_id="line_002",
                text="Hi!",
                speaker="Bob",
            ),
        ]

        result = format_lines_for_prompt(lines)

        assert "[line_001] [Alice]: Hello there!" in result
        assert "[line_002] [Bob]: Hi!" in result

    def test_format_without_speakers(self) -> None:
        """Test formatting lines without speakers."""
        lines = [
            SourceLine(
                line_id="line_001",
                text="Narration text",
            ),
        ]

        result = format_lines_for_prompt(lines)

        assert "[line_001]: Narration text" in result

    def test_format_empty_lines(self) -> None:
        """Test formatting empty list."""
        result = format_lines_for_prompt([])

        assert not result


class TestFormatAnnotatedLinesForPrompt:
    """Test cases for format_annotated_lines_for_prompt function."""

    def test_format_with_no_annotations(self) -> None:
        """Test formatting lines without annotations."""
        lines = [
            SourceLine(line_id="line_001", text="Hello", speaker="Alice"),
            SourceLine(line_id="line_002", text="World"),
        ]

        result = format_annotated_lines_for_prompt(lines, None)

        assert "[line_001] [Alice]: Hello" in result
        assert "[line_002]: World" in result

    def test_format_with_inline_annotations(self) -> None:
        """Test formatting lines with inline annotations."""
        lines = [
            SourceLine(line_id="line_001", text="猫の手も借りたい"),
        ]
        annotations = [
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="idiom",
                value="猫の手も借りたい",
                notes="Wanting to borrow even a cat's paws - very busy",
            ),
        ]

        result = format_annotated_lines_for_prompt(lines, annotations)

        # Line should be formatted first
        assert "[line_001]: 猫の手も借りたい" in result
        # Annotation should follow with indentation
        assert "^" in result
        assert "idiom" in result
        assert "猫の手も借りたい" in result

    def test_format_with_translation_hint(self) -> None:
        """Test formatting annotations with translation hints."""
        lines = [
            SourceLine(line_id="line_001", text="Test"),
        ]
        annotations = [
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="idiom",
                value="Test idiom",
                notes="Explanation",
                metadata={"translation_hint": "Use equivalent English idiom"},
            ),
        ]

        result = format_annotated_lines_for_prompt(lines, annotations)

        assert "[Hint:" in result
        assert "Use equivalent English idiom" in result

    def test_format_filters_annotations_to_lines(self) -> None:
        """Test that only annotations for the given lines are included."""
        lines = [
            SourceLine(line_id="line_001", text="Test"),
        ]
        annotations = [
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="idiom",
                value="Relevant",
                notes="Should be included",
            ),
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_999",
                annotation_type="idiom",
                value="Not relevant",
                notes="Should be filtered out",
            ),
        ]

        result = format_annotated_lines_for_prompt(lines, annotations)

        assert "Relevant" in result
        assert "Not relevant" not in result

    def test_format_empty_lines(self) -> None:
        """Test formatting empty lines list."""
        result = format_annotated_lines_for_prompt([], None)

        assert not result

    def test_format_multiple_annotations_per_line(self) -> None:
        """Test formatting multiple annotations for the same line."""
        lines = [
            SourceLine(line_id="line_001", text="Complex text"),
        ]
        annotations = [
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="idiom",
                value="First idiom",
                notes="First note",
            ),
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="pun",
                value="Second pun",
                notes="Second note",
            ),
        ]

        result = format_annotated_lines_for_prompt(lines, annotations)

        assert "First idiom" in result
        assert "Second pun" in result


class TestGetSceneSummaryForLines:
    """Test cases for get_scene_summary_for_lines function."""

    def test_get_summary_single_scene(self) -> None:
        """Test getting summary for single scene."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="B", scene_id="scene_001"),
        ]
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="First scene summary",
                characters=["Alice"],
            ),
        ]

        result = get_scene_summary_for_lines(lines, summaries)

        assert "scene_001" in result
        assert "First scene summary" in result

    def test_get_summary_no_summaries_available(self) -> None:
        """Test when no summaries are available."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
        ]

        result = get_scene_summary_for_lines(lines, None)

        assert result == "(No scene context available)"

    def test_get_summary_empty_summaries(self) -> None:
        """Test when summaries list is empty."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
        ]

        result = get_scene_summary_for_lines(lines, [])

        assert result == "(No scene context available)"

    def test_get_summary_no_scene_ids_in_lines(self) -> None:
        """Test when lines have no scene_id."""
        lines = [
            SourceLine(line_id="line_1", text="A"),
            SourceLine(line_id="line_2", text="B"),
        ]
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="First summary",
                characters=["Alice"],
            ),
        ]

        result = get_scene_summary_for_lines(lines, summaries)

        assert result == "(No scene context available)"


class TestFormatPretranslationAnnotations:
    """Test cases for format_pretranslation_annotations function."""

    def test_format_annotations_for_lines(self) -> None:
        """Test formatting annotations that match the lines."""
        lines = [
            SourceLine(line_id="line_001", text="猫の手も借りたい"),
        ]
        annotations = [
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="idiom",
                value="猫の手も借りたい",
                notes="Wanting to borrow even a cat's paws - very busy",
            ),
        ]

        result = format_pretranslation_annotations(lines, annotations)

        assert "line_001" in result
        assert "idiom" in result
        assert "猫の手も借りたい" in result

    def test_format_annotations_with_translation_hint(self) -> None:
        """Test formatting annotations with translation hints."""
        lines = [
            SourceLine(line_id="line_001", text="Test"),
        ]
        annotations = [
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="idiom",
                value="Test idiom",
                notes="Explanation",
                metadata={"translation_hint": "Use equivalent English idiom"},
            ),
        ]

        result = format_pretranslation_annotations(lines, annotations)

        assert "Hint:" in result
        assert "Use equivalent English idiom" in result

    def test_format_annotations_none(self) -> None:
        """Test when annotations is None."""
        lines = [
            SourceLine(line_id="line_001", text="Test"),
        ]

        result = format_pretranslation_annotations(lines, None)

        assert result == "(No pretranslation notes)"

    def test_format_annotations_empty(self) -> None:
        """Test when annotations list is empty."""
        lines = [
            SourceLine(line_id="line_001", text="Test"),
        ]

        result = format_pretranslation_annotations(lines, [])

        assert result == "(No pretranslation notes)"

    def test_format_annotations_filters_to_relevant_lines(self) -> None:
        """Test that only annotations for the given lines are included."""
        lines = [
            SourceLine(line_id="line_001", text="Test"),
        ]
        annotations = [
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_001",
                annotation_type="idiom",
                value="Relevant",
                notes="Should be included",
            ),
            PretranslationAnnotation(
                annotation_id=uuid7(),
                line_id="line_999",
                annotation_type="idiom",
                value="Not relevant",
                notes="Should be filtered out",
            ),
        ]

        result = format_pretranslation_annotations(lines, annotations)

        assert "Relevant" in result
        assert "Not relevant" not in result


class TestFormatGlossaryTerms:
    """Test cases for format_glossary_terms function."""

    def test_format_terms_with_notes(self) -> None:
        """Test formatting glossary terms with notes."""
        glossary = [
            GlossaryTerm(
                term="魔法",
                translation="magic",
                notes="Used for all magical abilities",
            ),
        ]

        result = format_glossary_terms(glossary)

        assert "魔法" in result
        assert "magic" in result
        assert "Used for all magical abilities" in result
        assert "→" in result

    def test_format_terms_without_notes(self) -> None:
        """Test formatting glossary terms without notes."""
        glossary = [
            GlossaryTerm(
                term="剣",
                translation="sword",
            ),
        ]

        result = format_glossary_terms(glossary)

        assert "剣" in result
        assert "sword" in result

    def test_format_glossary_none(self) -> None:
        """Test when glossary is None."""
        result = format_glossary_terms(None)

        assert result == "(No glossary terms)"

    def test_format_glossary_empty(self) -> None:
        """Test when glossary is empty."""
        result = format_glossary_terms([])

        assert result == "(No glossary terms)"

    def test_format_multiple_terms(self) -> None:
        """Test formatting multiple glossary terms."""
        glossary = [
            GlossaryTerm(term="Term1", translation="Translation1"),
            GlossaryTerm(term="Term2", translation="Translation2"),
        ]

        result = format_glossary_terms(glossary)

        assert "Term1" in result
        assert "Term2" in result


class TestTranslationResultToLines:
    """Test cases for translation_result_to_lines function."""

    def test_convert_basic_result(self) -> None:
        """Test converting a basic translation result."""
        result = TranslationResultList(
            translations=[
                TranslationResultLine(
                    line_id="line_001",
                    text="Hello!",
                ),
            ]
        )
        source_lines = [
            SourceLine(
                line_id="line_001",
                text="こんにちは!",
                scene_id="scene_001",
                speaker="Alice",
            ),
        ]

        translated = translation_result_to_lines(result, source_lines)

        assert len(translated) == 1
        assert translated[0].line_id == "line_001"
        assert translated[0].text == "Hello!"
        assert translated[0].scene_id == "scene_001"
        assert translated[0].speaker == "Alice"
        assert translated[0].source_text == "こんにちは!"

    def test_convert_preserves_metadata(self) -> None:
        """Test that metadata is preserved from source lines."""
        result = TranslationResultList(
            translations=[
                TranslationResultLine(
                    line_id="line_001",
                    text="Translated",
                ),
            ]
        )
        source_lines = [
            SourceLine(
                line_id="line_001",
                text="Source",
                route_id="route_001",
                scene_id="scene_001",
                speaker="Speaker",
                metadata={"key": "value"},
                source_columns=["col1", "col2"],
            ),
        ]

        translated = translation_result_to_lines(result, source_lines)

        assert translated[0].route_id == "route_001"
        assert translated[0].metadata == {"key": "value"}
        assert translated[0].source_columns == ["col1", "col2"]

    def test_convert_missing_source_line(self) -> None:
        """Test conversion when source line is not found."""
        result = TranslationResultList(
            translations=[
                TranslationResultLine(
                    line_id="line_999",
                    text="Translated without source",
                ),
            ]
        )
        source_lines = [
            SourceLine(
                line_id="line_001",
                text="Different source",
            ),
        ]

        with pytest.raises(ValueError, match="Translation alignment error"):
            translation_result_to_lines(result, source_lines)

    def test_convert_multiple_lines(self) -> None:
        """Test converting multiple translation results."""
        result = TranslationResultList(
            translations=[
                TranslationResultLine(line_id="line_001", text="Hello"),
                TranslationResultLine(line_id="line_002", text="World"),
            ]
        )
        source_lines = [
            SourceLine(line_id="line_001", text="こんにちは"),
            SourceLine(line_id="line_002", text="世界"),
        ]

        translated = translation_result_to_lines(result, source_lines)

        assert len(translated) == 2
        assert translated[0].text == "Hello"
        assert translated[1].text == "World"


class TestMergeTranslatedLines:
    """Test cases for merge_translated_lines function."""

    def test_merge_basic(self) -> None:
        """Test basic merging of translated lines."""
        run_id = uuid7()
        lines = [
            TranslatedLine(line_id="line_001", text="Hello"),
            TranslatedLine(line_id="line_002", text="World"),
        ]

        result = merge_translated_lines(run_id, "en", lines)

        assert result.run_id == run_id
        assert result.target_language == "en"
        assert len(result.translated_lines) == 2

    def test_merge_preserves_line_order(self) -> None:
        """Test that line order is preserved."""
        run_id = uuid7()
        lines = [
            TranslatedLine(line_id="line_003", text="Third"),
            TranslatedLine(line_id="line_001", text="First"),
            TranslatedLine(line_id="line_002", text="Second"),
        ]

        result = merge_translated_lines(run_id, "en", lines)

        assert result.translated_lines[0].line_id == "line_003"
        assert result.translated_lines[1].line_id == "line_001"
        assert result.translated_lines[2].line_id == "line_002"

    def test_merge_with_full_line_data(self) -> None:
        """Test merging lines with all metadata."""
        run_id = uuid7()
        lines = [
            TranslatedLine(
                line_id="line_001",
                text="Hello",
                route_id="route_001",
                scene_id="scene_001",
                speaker="Alice",
            ),
        ]

        result = merge_translated_lines(run_id, "en", lines)

        merged_line = result.translated_lines[0]
        assert merged_line.route_id == "route_001"
        assert merged_line.scene_id == "scene_001"
        assert merged_line.speaker == "Alice"
