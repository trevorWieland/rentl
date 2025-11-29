"""Unit tests for pipeline filtering logic."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.line import SourceLine, SourceLineMeta, TranslatedLine
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneAnnotations, SceneMetadata
from rentl_pipelines.flows.context_builder import (
    _filter_characters,
    _filter_locations,
    _filter_routes,
    _filter_scenes,
)
from rentl_pipelines.flows.editor import _filter_scenes_to_edit
from rentl_pipelines.flows.translator import _filter_scenes_to_translate


@pytest.fixture
def anyio_backend() -> str:
    """Force asyncio backend for anyio tests (trio not installed).

    Returns:
        str: The anyio backend name.
    """
    return "asyncio"


def _scene_with(
    *,
    id: str,
    summary: str | None = None,
    tags: list[str] | None = None,
    primary_characters: list[str] | None = None,
    locations: list[str] | None = None,
) -> SceneMetadata:
    annotations = SceneAnnotations(
        summary=summary,
        summary_origin="human" if summary else None,
        tags=tags or [],
        tags_origin="human" if tags else None,
        primary_characters=primary_characters or [],
        primary_characters_origin="human" if primary_characters else None,
        locations=locations or [],
        locations_origin="human" if locations else None,
    )
    return SceneMetadata(id=id, title=None, title_origin=None, route_ids=[], annotations=annotations)


def _character_with(id: str, *, name_tgt: str | None, pronouns: str | None, notes: str | None) -> CharacterMetadata:
    return CharacterMetadata(
        id=id,
        name_src=f"src-{id}",
        name_src_origin="human",
        name_tgt=name_tgt,
        name_tgt_origin="human" if name_tgt else None,
        pronouns=pronouns,
        pronouns_origin="human" if pronouns else None,
        notes=notes,
        notes_origin="human" if notes else None,
    )


def _location_with(id: str, *, name_tgt: str | None, description: str | None) -> LocationMetadata:
    return LocationMetadata(
        id=id,
        name_src=f"src-{id}",
        name_src_origin="human",
        name_tgt=name_tgt,
        name_tgt_origin="human" if name_tgt else None,
        description=description,
        description_origin="human" if description else None,
    )


def _route_with(id: str, *, synopsis: str | None, primary_characters: list[str] | None) -> RouteMetadata:
    return RouteMetadata(
        id=id,
        name=f"Route {id}",
        name_origin="human",
        scene_ids=[],
        synopsis=synopsis,
        synopsis_origin="human" if synopsis else None,
        primary_characters=primary_characters or [],
        primary_characters_origin="human" if primary_characters else None,
    )


def test_filter_scenes_gap_fill_and_new_only() -> None:
    """Scenes are filtered based on missing metadata and mode."""
    scenes = [
        _scene_with(id="full", summary="ok", tags=["a"], primary_characters=["mc"], locations=["loc"]),
        _scene_with(id="partial", summary="ok", tags=["a"], primary_characters=[], locations=[]),
        _scene_with(id="new", summary=None, tags=None, primary_characters=None, locations=None),
    ]

    gap_remaining, gap_skipped = _filter_scenes(scenes, "gap-fill")
    assert gap_remaining == ["new", "partial"]
    assert {entry.entity_id for entry in gap_skipped} == {"full"}

    new_remaining, new_skipped = _filter_scenes(scenes, "new-only")
    assert new_remaining == ["new"]
    assert {entry.entity_id for entry in new_skipped} == {"full", "partial"}

    overwrite_remaining, overwrite_skipped = _filter_scenes(scenes, "overwrite")
    assert overwrite_remaining == ["full", "new", "partial"]
    assert not overwrite_skipped


def test_filter_characters_locations_routes_gap_fill() -> None:
    """Characters/locations/routes are filtered by completeness and mode."""
    chars = [
        _character_with("c1", name_tgt="t", pronouns="p", notes="n"),
        _character_with("c2", name_tgt=None, pronouns=None, notes=None),
    ]
    locs = [
        _location_with("l1", name_tgt="t", description="d"),
        _location_with("l2", name_tgt=None, description=None),
    ]
    routes = [
        _route_with("r1", synopsis="s", primary_characters=["mc"]),
        _route_with("r2", synopsis=None, primary_characters=[]),
    ]

    assert _filter_characters(chars, "gap-fill") == ["c2"]
    assert _filter_characters(chars, "new-only") == ["c2"]
    assert _filter_locations(locs, "gap-fill") == ["l2"]
    assert _filter_locations(locs, "new-only") == ["l2"]
    assert _filter_routes(routes, "gap-fill") == ["r2"]
    assert _filter_routes(routes, "new-only") == ["r2"]


@pytest.mark.anyio("asyncio")
async def test_filter_scenes_to_translate(tmp_path: Path) -> None:
    """Translation filter respects mode and existing outputs."""

    class FakeContext:
        def __init__(self, base: Path) -> None:
            self.project_path = base
            self.translated: dict[str, int] = {}

        async def _load_translations(self, scene_id: str) -> None:
            """No-op for tests."""
            return None

        async def load_scene_lines(self, scene_id: str) -> list[SourceLine]:
            return [SourceLine(id=f"{scene_id}_1", text="a", meta=SourceLineMeta()) for _ in range(3)]

        def get_translated_line_count(self, scene_id: str) -> int:
            return self.translated.get(scene_id, 0)

    ctx = FakeContext(tmp_path)
    scene_ids = ["done", "partial", "none"]
    out_dir = tmp_path / "output" / "translations"
    out_dir.mkdir(parents=True, exist_ok=True)
    for sid in scene_ids:
        (out_dir / f"{sid}.jsonl").write_text("{}", encoding="utf-8")
    ctx.translated = {"done": 3, "partial": 1, "none": 0}

    remaining, skipped = await _filter_scenes_to_translate(ctx, scene_ids, "gap-fill", allow_overwrite=False)
    assert set(remaining) == {"partial", "none"}
    assert {entry.entity_id for entry in skipped} == {"done"}

    remaining_new, skipped_new = await _filter_scenes_to_translate(ctx, scene_ids, "new-only", allow_overwrite=False)
    assert remaining_new == ["none"]
    assert {entry.entity_id for entry in skipped_new} == {"done", "partial"}

    remaining_over, skipped_over = await _filter_scenes_to_translate(ctx, scene_ids, "overwrite", allow_overwrite=True)
    assert remaining_over == scene_ids
    assert not skipped_over


@pytest.mark.anyio("asyncio")
async def test_filter_scenes_to_edit() -> None:
    """Editor filter respects mode and QA coverage."""

    class FakeEditContext:
        def __init__(self, translations: dict[str, list[TranslatedLine]]) -> None:
            self._translations = translations

        async def _load_translations(self, scene_id: str) -> None:
            _ = scene_id

        async def get_translations(self, scene_id: str) -> list[TranslatedLine]:
            return self._translations.get(scene_id, [])

    base_line = SourceLine(id="line", text="src", meta=SourceLineMeta())
    checked_line = TranslatedLine.from_source(base_line, "tgt", text_tgt_origin="agent:test")
    checked_line = checked_line.model_copy(
        update={"meta": checked_line.meta.model_copy(update={"checks": {"style": (True, "")}})}
    )

    translations = {
        "full": [checked_line, checked_line],
        "partial": [
            checked_line,
            TranslatedLine.from_source(base_line, "other", text_tgt_origin="agent:test"),
        ],
        "none": [
            TranslatedLine.from_source(base_line, "first", text_tgt_origin="agent:test"),
            TranslatedLine.from_source(base_line, "second", text_tgt_origin="agent:test"),
        ],
        "untranslated": [],
    }
    ctx = FakeEditContext(translations)

    overwrite, skipped_overwrite = await _filter_scenes_to_edit(ctx, list(translations.keys()), "overwrite")
    assert overwrite == ["full", "partial", "none"]
    assert {entry.entity_id for entry in skipped_overwrite} == {"untranslated"}

    gap_fill, skipped_gap_fill = await _filter_scenes_to_edit(ctx, list(translations.keys()), "gap-fill")
    assert gap_fill == ["partial", "none"]
    assert {entry.entity_id for entry in skipped_gap_fill} == {"full", "untranslated"}

    new_only, skipped_new_only = await _filter_scenes_to_edit(ctx, list(translations.keys()), "new-only")
    assert new_only == ["none"]
    assert {entry.entity_id for entry in skipped_new_only} == {"full", "partial", "untranslated"}
