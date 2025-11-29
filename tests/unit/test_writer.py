"""Unit tests for rentl_core.io.writer helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_core.context.project import ProjectContext
from rentl_core.io.writer import write_qa_report
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.line import SourceLine, SourceLineMeta, TranslatedLine, TranslationMeta
from rentl_core.model.scene import SceneAnnotations, SceneMetadata


def _build_context_with_scene(tmp_path: Path, scene_lines: list[SourceLine]) -> ProjectContext:
    """Create a minimal ProjectContext with a scene file containing scene_lines.

    Returns:
        ProjectContext: Initialized context bound to the temp project paths.
    """
    metadata_dir = tmp_path / "metadata"
    scenes_dir = tmp_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    output_dir = tmp_path / "output"
    for directory in (metadata_dir, scenes_dir, context_docs_dir, output_dir):
        directory.mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="test",
        title_origin="human",
        description="",
        description_origin="human",
        source_lang="jpn",
        target_lang="eng",
        genres=[],
        genres_origin="human",
        synopsis="",
        synopsis_origin="human",
        timeline=[],
        ui=UIConstraints(max_line_length=42),
    )
    scene = SceneMetadata(
        id="scene_1",
        route_ids=[],
        title="Test Scene",
        title_origin="human",
        annotations=SceneAnnotations(
            summary=None,
            summary_origin=None,
            tags=[],
            tags_origin=None,
            primary_characters=[],
            primary_characters_origin=None,
            locations=[],
            locations_origin=None,
        ),
    )
    # Seed scene file
    scene_file = scenes_dir / f"{scene.id}.jsonl"
    scene_file.write_text("\n".join(line.model_dump_json(exclude_none=True) for line in scene_lines) + "\n")

    return ProjectContext(
        project_path=tmp_path,
        game=game,
        characters={},
        glossary=[],
        locations={},
        routes={},
        scenes={scene.id: scene},
        metadata_dir=metadata_dir,
        scenes_dir=scenes_dir,
        context_docs_dir=context_docs_dir,
        output_dir=output_dir,
    )


@pytest.mark.anyio
async def test_write_translation_respects_source_order(tmp_path: Path) -> None:
    """record_translation/_write_translations should follow source line order."""
    scene_lines = [
        SourceLine(id="l2", text="two", meta=SourceLineMeta()),
        SourceLine(id="l1", text="one", meta=SourceLineMeta()),
    ]
    context = _build_context_with_scene(tmp_path, scene_lines)

    # Record out of order; persistence should reorder to source order
    await context.record_translation(
        "scene_1", TranslatedLine(id="l1", text_src="one", text_tgt="ONE", text_tgt_origin="agent:test")
    )
    await context.record_translation(
        "scene_1", TranslatedLine(id="l2", text_src="two", text_tgt="TWO", text_tgt_origin="agent:test")
    )

    output = tmp_path / "output" / "translations" / "scene_1.jsonl"
    lines = output.read_text().splitlines()
    assert len(lines) == 2
    assert '"id":"l2"' in lines[0]  # first source line
    assert '"id":"l1"' in lines[1]
    assert output.read_bytes().endswith(b"\n")


@pytest.mark.anyio
async def test_write_translation_appends_extra_at_end(tmp_path: Path) -> None:
    """Translations without source lines should append after ordered ones."""
    scene_lines = [SourceLine(id="l1", text="one", meta=SourceLineMeta())]
    context = _build_context_with_scene(tmp_path, scene_lines)

    await context.record_translation(
        "scene_1", TranslatedLine(id="l3", text_src="three", text_tgt="THREE", text_tgt_origin="agent:test")
    )
    await context.record_translation(
        "scene_1", TranslatedLine(id="l2", text_src="two", text_tgt="TWO", text_tgt_origin="agent:test")
    )
    await context.record_translation(
        "scene_1", TranslatedLine(id="l1", text_src="one", text_tgt="ONE", text_tgt_origin="agent:test")
    )

    output = tmp_path / "output" / "translations" / "scene_1.jsonl"
    lines = output.read_text().splitlines()
    assert '"id":"l1"' in lines[0]
    assert '"id":"l2"' in lines[1]
    assert '"id":"l3"' in lines[2]


@pytest.mark.anyio
async def test_write_qa_report_only_lists_failed_checks(tmp_path: Path) -> None:
    """QA report should list only failures and show success message when none."""
    output = tmp_path / "report.txt"
    ok_line = TranslatedLine(
        id="l1",
        text_src="src",
        text_tgt="tgt",
        text_tgt_origin="agent:test",
        meta=TranslationMeta(checks={"style": (True, "ok"), "length": (True, "")}),
    )
    fail_line = TranslatedLine(
        id="l2",
        text_src="src2",
        text_tgt="tgt2",
        text_tgt_origin="agent:test",
        meta=TranslationMeta(checks={"style": (False, "bad"), "length": (True, "")}),
    )

    await write_qa_report(output, [ok_line, fail_line], "scene_x")
    text = output.read_text()
    assert "FAILED CHECKS" in text
    assert "style" in text
    assert "bad" in text
    if "length" in text:
        assert "bad" not in text


@pytest.mark.anyio
async def test_write_qa_report_all_passes_message(tmp_path: Path) -> None:
    """QA report should emit 'All checks passed!' when nothing failed."""
    output = tmp_path / "report.txt"
    ok_line = TranslatedLine(
        id="l1",
        text_src="src",
        text_tgt="tgt",
        text_tgt_origin="agent:test",
        meta=TranslationMeta(checks={"style": (True, "")}),
    )

    await write_qa_report(output, [ok_line], "scene_y")
    text = output.read_text()
    assert "All checks passed!" in text
