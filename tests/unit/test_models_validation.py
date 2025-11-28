"""Validation tests for core models and loaders."""

from __future__ import annotations

from pathlib import Path

import orjson
import pytest
from rentl_core.io.loader import load_scene_metadata
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.game import GameMetadata
from rentl_core.model.scene import SceneMetadata


def test_game_metadata_requires_origins() -> None:
    """Setting fields without *_origin should raise validation errors."""
    with pytest.raises(ValueError, match="title_origin is required"):
        GameMetadata(
            title="Test",
            source_lang="jpn",
            target_lang="eng",
            title_origin=None,
        )


@pytest.mark.anyio
async def test_load_scene_metadata_raises_on_invalid_json(tmp_path: Path) -> None:
    """Invalid JSONL should surface JSONDecodeError."""
    path = tmp_path / "bad.jsonl"
    path.write_text("not json\n")

    with pytest.raises(orjson.JSONDecodeError):
        await load_scene_metadata(path)


def test_character_requires_provenance_when_values_present() -> None:
    """Characters with set fields must include corresponding origins."""
    with pytest.raises(ValueError, match="name_tgt_origin"):
        CharacterMetadata(
            id="aya",
            name_src="Aya",
            name_tgt="Aya",
            # missing name_tgt_origin should fail
            name_src_origin="human",
        )


def test_scene_annotations_require_origins() -> None:
    """SceneAnnotations should enforce *_origin when fields are set."""
    with pytest.raises(ValueError, match="summary_origin"):
        SceneMetadata(
            id="scene01",
            annotations=SceneMetadata.model_fields["annotations"].annotation(  # type: ignore[arg-type]
                summary="summary text"
            ),
        )
