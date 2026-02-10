"""Integration tests for eval set download flow with mocked HTTP."""

import hashlib
from collections.abc import Generator
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest
import respx

from rentl_core.benchmark.eval_sets.aligner import LineAligner
from rentl_core.benchmark.eval_sets.downloader import KatawaShoujoDownloader
from rentl_core.benchmark.eval_sets.parser import RenpyDialogueParser


@pytest.mark.asyncio
class TestDownloadFlow:
    """Integration tests for download flow with mocked HTTP."""

    @pytest.fixture
    def temp_cache(self) -> Generator[Path]:
        """Create a temporary cache directory.

        Yields:
            Path to temporary cache directory
        """
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @respx.mock
    async def test_download_single_script(self, temp_cache: Path) -> None:
        """Downloader fetches and caches a single script file."""
        script_content = b'hisao "Test dialogue."'
        script_hash = hashlib.sha256(script_content).hexdigest()

        # Mock the HTTP request
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/test.rpy"
        ).mock(return_value=httpx.Response(200, content=script_content))

        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)
        results = await downloader.download_scripts(
            ["test.rpy"],
            hash_manifest={"test.rpy": script_hash},
        )

        assert "test.rpy" in results
        assert results["test.rpy"].exists()
        assert results["test.rpy"].read_bytes() == script_content

    @respx.mock
    async def test_download_hash_validation_fails(self, temp_cache: Path) -> None:
        """Downloader raises ValueError when hash validation fails."""
        script_content = b'hisao "Test dialogue."'
        wrong_hash = "0" * 64  # Intentionally wrong hash

        # Mock the HTTP request
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/test.rpy"
        ).mock(return_value=httpx.Response(200, content=script_content))

        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)

        with pytest.raises(ValueError, match="Hash validation failed"):
            await downloader.download_scripts(
                ["test.rpy"],
                hash_manifest={"test.rpy": wrong_hash},
            )

        # File should be removed after failed validation
        cached_path = temp_cache / "test.rpy"
        assert not cached_path.exists()

    @respx.mock
    async def test_download_uses_cache(self, temp_cache: Path) -> None:
        """Downloader skips download when file is cached with correct hash."""
        script_content = b'hisao "Test dialogue."'
        script_hash = hashlib.sha256(script_content).hexdigest()

        # Pre-populate cache
        cached_path = temp_cache / "test.rpy"
        cached_path.write_bytes(script_content)

        # Mock should NOT be called if cache is used
        mock_route = respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/test.rpy"
        ).mock(return_value=httpx.Response(200, content=script_content))

        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)
        results = await downloader.download_scripts(
            ["test.rpy"],
            hash_manifest={"test.rpy": script_hash},
        )

        assert "test.rpy" in results
        assert results["test.rpy"].exists()
        assert not mock_route.called

    @respx.mock
    async def test_download_multiple_scripts_with_progress(
        self, temp_cache: Path
    ) -> None:
        """Downloader handles multiple files and reports progress."""
        script1_content = b'hisao "First script."'
        script2_content = b'emi "Second script."'

        # Mock HTTP requests
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/script1.rpy"
        ).mock(return_value=httpx.Response(200, content=script1_content))
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/script2.rpy"
        ).mock(return_value=httpx.Response(200, content=script2_content))

        progress_calls: list[tuple[str, int, int]] = []

        def track_progress(file_name: str, current: int, total: int) -> None:
            progress_calls.append((file_name, current, total))

        downloader = KatawaShoujoDownloader(
            cache_dir=temp_cache,
            progress_callback=track_progress,
        )

        results = await downloader.download_scripts(["script1.rpy", "script2.rpy"])

        assert len(results) == 2
        assert "script1.rpy" in results
        assert "script2.rpy" in results

        # Progress callback should be called for each file
        assert len(progress_calls) == 2
        assert progress_calls[0] == ("script1.rpy", 1, 2)
        assert progress_calls[1] == ("script2.rpy", 2, 2)

    @respx.mock
    async def test_download_http_error_propagates(self, temp_cache: Path) -> None:
        """Downloader propagates HTTP errors."""
        # Mock 404 response
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/missing.rpy"
        ).mock(return_value=httpx.Response(404))

        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)

        with pytest.raises(httpx.HTTPStatusError):
            await downloader.download_scripts(["missing.rpy"])

    @respx.mock
    async def test_download_enforces_manifest_coverage(self, temp_cache: Path) -> None:
        """Downloader raises ValueError when script not in manifest."""
        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)

        # Manifest is provided but doesn't contain the requested script
        manifest = {"other.rpy": "abc123"}

        with pytest.raises(
            ValueError,
            match=r"Script 'test\.rpy' not found in hash manifest",
        ):
            await downloader.download_scripts(["test.rpy"], hash_manifest=manifest)

    @respx.mock
    async def test_download_parse_align_end_to_end(self, temp_cache: Path) -> None:
        """Full end-to-end flow: download -> parse -> align."""
        # Mock Japanese source script
        ja_content = b"""# Japanese source
hisao "\xe3\x81\x93\xe3\x82\x93\xe3\x81\xab\xe3\x81\xa1\xe3\x81\xaf"
emi "\xe3\x82\x84\xe3\x81\x82\xef\xbc\x81"
"""
        ja_hash = hashlib.sha256(ja_content).hexdigest()

        # Mock English reference script
        en_content = b"""# English reference
hisao "Hello"
emi "Hey!"
"""
        en_hash = hashlib.sha256(en_content).hexdigest()

        # Mock HTTP requests
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/ja-script.rpy"
        ).mock(return_value=httpx.Response(200, content=ja_content))
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/en-script.rpy"
        ).mock(return_value=httpx.Response(200, content=en_content))

        # Download
        downloader = KatawaShoujoDownloader(cache_dir=temp_cache)
        results = await downloader.download_scripts(
            ["ja-script.rpy", "en-script.rpy"],
            hash_manifest={
                "ja-script.rpy": ja_hash,
                "en-script.rpy": en_hash,
            },
        )

        # Parse both scripts
        parser = RenpyDialogueParser()
        ja_lines = parser.parse_script(results["ja-script.rpy"])
        parser_en = RenpyDialogueParser()  # Fresh parser for different scene
        en_lines = parser_en.parse_script(results["en-script.rpy"])

        # Verify parsing worked
        assert len(ja_lines) == 2
        assert ja_lines[0].speaker == "hisao"
        assert len(en_lines) == 2
        assert en_lines[0].speaker == "hisao"
        assert en_lines[0].text == "Hello"

        # Align by position (since auto-normalized scene_ids differ)
        aligner = LineAligner()
        aligned = aligner.align_by_position(ja_lines, en_lines)

        assert len(aligned) == 2
        assert aligned[0].source.speaker == "hisao"
        assert aligned[0].reference is not None
        assert aligned[0].reference.text == "Hello"
        assert aligned[1].source.speaker == "emi"
        assert aligned[1].reference is not None
        assert aligned[1].reference.text == "Hey!"
