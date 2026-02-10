"""Unit tests for EvalSetLoader."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from rentl_core.benchmark.eval_sets.downloader import KatawaShoujoDownloader
from rentl_core.benchmark.eval_sets.loader import EvalSetLoader
from rentl_core.benchmark.eval_sets.parser import RenpyDialogueParser


class TestEvalSetLoader:
    """Test suite for eval set configuration loader."""

    def test_load_manifest_katawa_shoujo(self) -> None:
        """Loader successfully loads Katawa Shoujo manifest."""
        manifest = EvalSetLoader.load_manifest("katawa_shoujo")

        assert manifest.eval_set_id == "katawa-shoujo"
        assert manifest.description
        assert manifest.source
        assert isinstance(manifest.scripts, dict)
        assert len(manifest.scripts) > 0

    def test_load_slices_katawa_shoujo(self) -> None:
        """Loader successfully loads Katawa Shoujo slices config."""
        slices_config = EvalSetLoader.load_slices("katawa_shoujo")

        assert "demo" in slices_config.slices
        demo_slice = slices_config.slices["demo"]
        assert demo_slice.description
        assert len(demo_slice.scripts) > 0
        assert demo_slice.scripts[0].file
        assert len(demo_slice.scripts[0].line_range) == 2

    def test_get_slice_scripts_demo(self) -> None:
        """Loader extracts script list for demo slice."""
        scripts = EvalSetLoader.get_slice_scripts("katawa_shoujo", "demo")

        assert isinstance(scripts, list)
        assert len(scripts) > 0
        assert all(script.endswith(".rpy") for script in scripts)

    def test_get_slice_scripts_invalid_slice(self) -> None:
        """Loader raises KeyError for invalid slice name."""
        with pytest.raises(KeyError, match="not found"):
            EvalSetLoader.get_slice_scripts("katawa_shoujo", "nonexistent")

    def test_load_manifest_invalid_eval_set(self) -> None:
        """Loader raises FileNotFoundError for invalid eval set."""
        with pytest.raises(FileNotFoundError, match="Manifest not found"):
            EvalSetLoader.load_manifest("nonexistent_eval_set")

    def test_load_slices_invalid_eval_set(self) -> None:
        """Loader raises FileNotFoundError for invalid eval set."""
        with pytest.raises(FileNotFoundError, match="Slices config not found"):
            EvalSetLoader.load_slices("nonexistent_eval_set")

    def test_manifest_scripts_have_valid_hashes(self) -> None:
        """All manifest script hashes are valid SHA-256 format."""
        manifest = EvalSetLoader.load_manifest("katawa_shoujo")

        for _filename, hash_value in manifest.scripts.items():
            # SHA-256 hashes are 64 hexadecimal characters
            assert len(hash_value) == 64
            assert all(c in "0123456789abcdef" for c in hash_value)

    def test_demo_slice_scripts_exist_in_manifest(self) -> None:
        """All scripts in demo slice have corresponding manifest entries."""
        manifest = EvalSetLoader.load_manifest("katawa_shoujo")
        demo_scripts = EvalSetLoader.get_slice_scripts("katawa_shoujo", "demo")

        for script in demo_scripts:
            assert script in manifest.scripts, (
                f"Script '{script}' in demo slice not found in manifest"
            )

    def test_demo_slice_contains_required_content_types(self) -> None:
        """Demo slice includes dialogue, narration, choices, and multiple speakers.

        This validates that the configured demo slice meets the Task 3
        requirement for mixed content types suitable for parser/judge testing.
        """
        # Load slice config
        slices_config = EvalSetLoader.load_slices("katawa_shoujo")
        demo_slice = slices_config.slices["demo"]

        # Get the script file and line range
        assert len(demo_slice.scripts) > 0, "Demo slice must have at least one script"
        script_spec = demo_slice.scripts[0]
        script_file = script_spec.file
        line_start, line_end = script_spec.line_range

        # Download the script (with hash validation)
        manifest = EvalSetLoader.load_manifest("katawa_shoujo")

        with TemporaryDirectory() as tmpdir:
            downloader = KatawaShoujoDownloader(cache_dir=Path(tmpdir))

            script_paths = asyncio.run(
                downloader.download_scripts([script_file], manifest.scripts)
            )

            # Parse the script
            parser = RenpyDialogueParser()
            all_lines = parser.parse_script(script_paths[script_file])

            # Filter to the configured line range (by source_line metadata)
            slice_lines = []
            for line in all_lines:
                if line.metadata is None:
                    continue
                source_line = line.metadata.get("source_line", 0)
                if (
                    isinstance(source_line, int)
                    and line_start <= source_line <= line_end
                ):
                    slice_lines.append(line)

            # Collect content properties
            has_dialogue = any(
                line.speaker and line.speaker != "[menu]" for line in slice_lines
            )
            has_narration = any(line.speaker is None for line in slice_lines)
            has_choices = any(
                line.metadata is not None and line.metadata.get("type") == "choice"
                for line in slice_lines
            )
            named_speakers = {
                line.speaker
                for line in slice_lines
                if line.speaker and line.speaker != "[menu]"
            }

            # Assert required content mix
            assert len(slice_lines) >= 20, (
                f"Demo slice should have at least 20 parseable lines, "
                f"got {len(slice_lines)}"
            )
            assert has_dialogue, "Demo slice must include dialogue with speakers"
            assert has_narration, "Demo slice must include narration (no speaker)"
            assert has_choices, "Demo slice must include menu choices"
            assert len(named_speakers) >= 2, (
                f"Demo slice must have at least 2 named speakers, got {named_speakers}"
            )
