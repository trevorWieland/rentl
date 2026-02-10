"""Unit tests for EvalSetLoader."""

import pytest

from rentl_core.benchmark.eval_sets.loader import EvalSetLoader


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
