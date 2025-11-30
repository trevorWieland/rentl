"""Tests for context docs and style guide helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_core.context.project import ProjectContext
from rentl_core.model.game import GameMetadata, UIConstraints
from rentl_core.model.scene import SceneAnnotations, SceneMetadata

from tests.helpers.tool_builders import build_context_doc_tools


def _base_context(tmp_path: Path) -> ProjectContext:
    """Return a minimal ProjectContext with empty context_docs and style guide."""
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
        title="Test",
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
async def test_context_docs_list_and_read(tmp_path: Path) -> None:
    """list_context_docs/read_context_doc should handle missing and present files."""
    context = _base_context(tmp_path)
    tools = build_context_doc_tools(context)
    list_docs = next(t for t in tools if t.name == "list_context_docs")
    read_doc = next(t for t in tools if t.name == "read_context_doc")

    # Missing yields placeholder
    missing = await read_doc.coroutine(filename="missing.md")  # type: ignore[attr-defined]
    assert "not found" in missing.lower()

    # Add a file and re-list/read
    doc_path = context.context_docs_dir / "notes.md"
    doc_path.write_text("hello")
    listed = await list_docs.coroutine()  # type: ignore[attr-defined]
    assert "notes.md" in listed
    content = await read_doc.coroutine(filename="notes.md")  # type: ignore[attr-defined]
    assert content == "hello"


@pytest.mark.anyio
async def test_read_style_guide_fallback(tmp_path: Path) -> None:
    """read_style_guide should return fallback when file is missing, else contents."""
    context = _base_context(tmp_path)
    missing = await context.read_style_guide()
    assert "No style guide found" in missing

    style_path = context.metadata_dir / "style_guide.md"
    style_path.write_text("Style Guide\n- Keep it tight")
    present = await context.read_style_guide()
    assert "Keep it tight" in present
