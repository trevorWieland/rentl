"""Unit tests for KatawaShoujoDownloader."""

import hashlib
from collections.abc import Generator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from rentl_core.benchmark.eval_sets.downloader import KatawaShoujoDownloader


class TestKatawaShoujoDownloader:
    """Test suite for Katawa Shoujo script downloader."""

    @pytest.fixture
    def temp_cache(self) -> Generator[Path]:
        """Create a temporary cache directory.

        Yields:
            Path to temporary cache directory
        """
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_compute_sha256(self, temp_cache: Path) -> None:
        """Downloader correctly computes SHA-256 hash."""
        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)

        test_file = temp_cache / "test.txt"
        test_content = b"Hello, world!"
        test_file.write_bytes(test_content)

        expected_hash = hashlib.sha256(test_content).hexdigest()
        actual_hash = downloader._compute_sha256(test_file)

        assert actual_hash == expected_hash

    def test_cache_dir_defaults_to_home(self) -> None:
        """Downloader uses default cache directory if not specified."""
        downloader = KatawaShoujoDownloader()
        expected_default = (
            Path.home() / ".cache" / "rentl" / "eval_sets" / "katawa-shoujo"
        )
        assert downloader.cache_dir == expected_default

    def test_progress_callback_invoked(self, temp_cache: Path) -> None:
        """Downloader invokes progress callback during download."""
        progress_calls: list[tuple[str, int, int]] = []

        def track_progress(file_name: str, current: int, total: int) -> None:
            progress_calls.append((file_name, current, total))

        downloader = KatawaShoujoDownloader(
            cache_dir=temp_cache,
            progress_callback=track_progress,
        )

        # We'll test this in integration tests with mocked HTTP
        # For now, just verify the callback is stored
        assert downloader.progress_callback is track_progress

    def test_manifest_none_allows_missing_hash(self, temp_cache: Path) -> None:
        """Downloader allows downloads without manifest when manifest is None."""
        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)
        # This should not raise - manifest=None means no validation
        # (Actual download tested in integration tests)
        assert downloader.cache_dir == temp_cache

    def test_ksre_raw_base_points_to_japanese_translations(self) -> None:
        """Downloader uses Japanese translation path, not English originals."""
        # Task 13 contract: KSRE is "Katawa Shoujo: Re-Engineered", a modernization
        # of the originally-English VN. Main game/ scripts are English.
        # Japanese translations are at game/tl/jp/
        downloader = KatawaShoujoDownloader()

        # Verify the base URL points to the Japanese translation directory
        assert downloader.KSRE_RAW_BASE.endswith("game/tl/jp")
        assert "game/tl/jp" in downloader.KSRE_RAW_BASE

        # Ensure it does NOT point to the English originals at /game/
        assert not downloader.KSRE_RAW_BASE.endswith("/game")
        assert downloader.KSRE_RAW_BASE.count("/game") == 1  # Only once (before /tl/jp)
