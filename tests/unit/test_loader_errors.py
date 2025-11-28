"""Loader error cases to ensure failures surface clearly."""

from __future__ import annotations

from pathlib import Path

import pytest
from rentl_core.io.loader import load_scene_metadata


@pytest.mark.anyio
async def test_load_scene_metadata_missing_file(tmp_path: Path) -> None:
    """Missing scene metadata should raise FileNotFoundError."""
    missing = tmp_path / "missing.jsonl"
    with pytest.raises(FileNotFoundError):
        await load_scene_metadata(missing)
