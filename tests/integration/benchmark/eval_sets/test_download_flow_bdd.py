"""BDD integration tests for eval set download flow with mocked HTTP."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest
import respx
from pytest_bdd import given, scenarios, then, when

from rentl_core.benchmark.eval_sets.aligner import LineAligner
from rentl_core.benchmark.eval_sets.downloader import KatawaShoujoDownloader
from rentl_core.benchmark.eval_sets.parser import RenpyDialogueParser
from rentl_io.ingest.jsonl_adapter import JsonlIngestAdapter
from rentl_schemas.io import IngestSource
from rentl_schemas.primitives import FileFormat

if TYPE_CHECKING:
    from rentl_core.benchmark.eval_sets.aligner import AlignedLinePair
    from rentl_schemas.io import SourceLine

# Link feature file
scenarios("../../../features/benchmark/eval_set_download.feature")


class DownloadFlowContext:
    """Context object for eval set download BDD scenarios."""

    def __init__(self) -> None:
        """Initialize context."""
        self.temp_cache: Path | None = None
        self.script_content: bytes = b""
        self.script_hash: str = ""
        self.wrong_hash: str = ""
        self.downloader: KatawaShoujoDownloader | None = None
        self.results: dict[str, Path] | None = None
        self.error: Exception | None = None
        self.progress_calls: list[tuple[str, int, int]] = []
        self.mock_route: respx.Route | None = None
        self.ja_lines: list[SourceLine] = []
        self.en_lines: list[SourceLine] = []
        self.aligned: list[AlignedLinePair] = []
        self.parsed_lines: list[SourceLine] = []
        self.jsonl_path: Path | None = None
        self.ingested_lines: list[SourceLine] = []


@pytest.fixture
def ctx(tmp_path: Path) -> DownloadFlowContext:
    """Create a fresh context for each scenario.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        DownloadFlowContext with temp cache initialized.
    """
    context = DownloadFlowContext()
    context.temp_cache = tmp_path
    return context


@given("a mock HTTP server with a valid script")
def given_mock_http_with_valid_script(ctx: DownloadFlowContext) -> None:
    """Set up a mock HTTP server with a valid script.

    Args:
        ctx: Download flow context.
    """
    ctx.script_content = b'hisao "Test dialogue."'
    ctx.script_hash = hashlib.sha256(ctx.script_content).hexdigest()


@given("a mock HTTP server that returns 404")
def given_mock_http_with_404(ctx: DownloadFlowContext) -> None:
    """Set up a mock HTTP server that returns 404.

    Args:
        ctx: Download flow context.
    """
    # Mock 404 response (Task 13: Japanese translations at game/tl/jp)
    with respx.mock:
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/missing.rpy"
        ).mock(return_value=httpx.Response(404))


@given("a script is already cached with correct hash")
def given_script_cached(ctx: DownloadFlowContext) -> None:
    """Pre-populate cache with a script.

    Args:
        ctx: Download flow context.
    """
    ctx.script_content = b'hisao "Test dialogue."'
    ctx.script_hash = hashlib.sha256(ctx.script_content).hexdigest()

    # Pre-populate cache
    assert ctx.temp_cache is not None
    cached_path = ctx.temp_cache / "test.rpy"
    cached_path.write_bytes(ctx.script_content)


@given("a hash manifest that excludes a script")
def given_manifest_excludes_script(ctx: DownloadFlowContext) -> None:
    """Set up a manifest that excludes the requested script.

    Args:
        ctx: Download flow context.
    """
    # Context will use manifest that doesn't contain test.rpy
    pass


@given("a mock HTTP server with multiple scripts")
def given_mock_http_with_multiple_scripts(ctx: DownloadFlowContext) -> None:
    """Set up a mock HTTP server with multiple scripts.

    Args:
        ctx: Download flow context.
    """
    # Multiple scripts will be mocked in the when step
    pass


@given("a mock HTTP server with Japanese and English scripts")
def given_mock_http_with_ja_en_scripts(ctx: DownloadFlowContext) -> None:
    """Set up a mock HTTP server with Japanese and English scripts.

    Args:
        ctx: Download flow context.
    """
    # Scripts will be mocked in the when step
    pass


@when("I download the script with correct hash")
def when_download_with_correct_hash(ctx: DownloadFlowContext) -> None:
    """Download a script with correct hash.

    Args:
        ctx: Download flow context.
    """
    with respx.mock:
        # Mock the HTTP request (Task 13: Japanese translations at game/tl/jp)
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/test.rpy"
        ).mock(return_value=httpx.Response(200, content=ctx.script_content))

        assert ctx.temp_cache is not None
        ctx.downloader = KatawaShoujoDownloader(cache_dir=ctx.temp_cache)

        # Run async code synchronously
        ctx.results = asyncio.run(
            ctx.downloader.download_scripts(
                ["test.rpy"],
                hash_manifest={"test.rpy": ctx.script_hash},
            )
        )


@when("I download the script with wrong hash")
def when_download_with_wrong_hash(ctx: DownloadFlowContext) -> None:
    """Download a script with wrong hash.

    Args:
        ctx: Download flow context.
    """
    ctx.wrong_hash = "0" * 64  # Intentionally wrong hash

    with respx.mock:
        # Mock the HTTP request (Task 13: Japanese translations at game/tl/jp)
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/test.rpy"
        ).mock(return_value=httpx.Response(200, content=ctx.script_content))

        assert ctx.temp_cache is not None
        ctx.downloader = KatawaShoujoDownloader(cache_dir=ctx.temp_cache)

        try:
            asyncio.run(
                ctx.downloader.download_scripts(
                    ["test.rpy"],
                    hash_manifest={"test.rpy": ctx.wrong_hash},
                )
            )
        except ValueError as e:
            ctx.error = e


@when("I attempt to download the script")
def when_attempt_download_cached(ctx: DownloadFlowContext) -> None:
    """Attempt to download a script that's already cached.

    Args:
        ctx: Download flow context.
    """
    with respx.mock:
        # Mock should NOT be called if cache is used
        # (Task 13: Japanese translations at game/tl/jp)
        ctx.mock_route = respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/test.rpy"
        ).mock(return_value=httpx.Response(200, content=ctx.script_content))

        assert ctx.temp_cache is not None
        ctx.downloader = KatawaShoujoDownloader(cache_dir=ctx.temp_cache)

        ctx.results = asyncio.run(
            ctx.downloader.download_scripts(
                ["test.rpy"],
                hash_manifest={"test.rpy": ctx.script_hash},
            )
        )


@when("I download all scripts")
def when_download_all_scripts(ctx: DownloadFlowContext) -> None:
    """Download multiple scripts.

    Args:
        ctx: Download flow context.
    """
    script1_content = b'hisao "First script."'
    script2_content = b'emi "Second script."'

    with respx.mock:
        # Mock HTTP requests (Task 13: Japanese translations at game/tl/jp)
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/script1.rpy"
        ).mock(return_value=httpx.Response(200, content=script1_content))
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/script2.rpy"
        ).mock(return_value=httpx.Response(200, content=script2_content))

        def track_progress(file_name: str, current: int, total: int) -> None:
            ctx.progress_calls.append((file_name, current, total))

        assert ctx.temp_cache is not None
        ctx.downloader = KatawaShoujoDownloader(
            cache_dir=ctx.temp_cache,
            progress_callback=track_progress,
        )

        ctx.results = asyncio.run(
            ctx.downloader.download_scripts(["script1.rpy", "script2.rpy"])
        )


@when("I attempt to download a missing script")
def when_download_missing_script(ctx: DownloadFlowContext) -> None:
    """Attempt to download a missing script.

    Args:
        ctx: Download flow context.
    """
    with respx.mock:
        # Mock 404 response (Task 13: Japanese translations at game/tl/jp)
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/missing.rpy"
        ).mock(return_value=httpx.Response(404))

        assert ctx.temp_cache is not None
        ctx.downloader = KatawaShoujoDownloader(cache_dir=ctx.temp_cache)

        try:
            asyncio.run(ctx.downloader.download_scripts(["missing.rpy"]))
        except httpx.HTTPStatusError as e:
            ctx.error = e


@when("I attempt to download the excluded script")
def when_download_excluded_script(ctx: DownloadFlowContext) -> None:
    """Attempt to download a script not in the manifest.

    Args:
        ctx: Download flow context.
    """
    assert ctx.temp_cache is not None
    ctx.downloader = KatawaShoujoDownloader(cache_dir=ctx.temp_cache)

    # Manifest is provided but doesn't contain the requested script
    manifest = {"other.rpy": "abc123"}

    try:
        asyncio.run(
            ctx.downloader.download_scripts(["test.rpy"], hash_manifest=manifest)
        )
    except ValueError as e:
        ctx.error = e


@when("I download both scripts")
def when_download_both_scripts(ctx: DownloadFlowContext) -> None:
    """Download both Japanese and English scripts.

    Args:
        ctx: Download flow context.
    """
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

    with respx.mock:
        # Mock HTTP requests (Task 13: Japanese translations at game/tl/jp)
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/ja-script.rpy"
        ).mock(return_value=httpx.Response(200, content=ja_content))
        respx.get(
            "https://raw.githubusercontent.com/fleetingheart/ksre/master/game/tl/jp/en-script.rpy"
        ).mock(return_value=httpx.Response(200, content=en_content))

        # Download
        assert ctx.temp_cache is not None
        ctx.downloader = KatawaShoujoDownloader(cache_dir=ctx.temp_cache)

        ctx.results = asyncio.run(
            ctx.downloader.download_scripts(
                ["ja-script.rpy", "en-script.rpy"],
                hash_manifest={
                    "ja-script.rpy": ja_hash,
                    "en-script.rpy": en_hash,
                },
            )
        )


@when("I parse both scripts with RenpyDialogueParser")
def when_parse_both_scripts(ctx: DownloadFlowContext) -> None:
    """Parse both downloaded scripts.

    Args:
        ctx: Download flow context.
    """
    assert ctx.results is not None
    parser = RenpyDialogueParser()
    ctx.ja_lines = parser.parse_script(ctx.results["ja-script.rpy"])
    parser_en = RenpyDialogueParser()  # Fresh parser for different scene
    ctx.en_lines = parser_en.parse_script(ctx.results["en-script.rpy"])


@when("I align the parsed lines")
def when_align_parsed_lines(ctx: DownloadFlowContext) -> None:
    """Align parsed lines by position.

    Args:
        ctx: Download flow context.
    """
    aligner = LineAligner()
    ctx.aligned = aligner.align_by_position(ctx.ja_lines, ctx.en_lines)


@then("the script is cached to disk")
def then_script_cached(ctx: DownloadFlowContext) -> None:
    """Verify script is cached to disk.

    Args:
        ctx: Download flow context.
    """
    assert ctx.results is not None
    assert "test.rpy" in ctx.results
    assert ctx.results["test.rpy"].exists()


@then("the script content matches")
def then_script_content_matches(ctx: DownloadFlowContext) -> None:
    """Verify script content matches original.

    Args:
        ctx: Download flow context.
    """
    assert ctx.results is not None
    assert ctx.results["test.rpy"].read_bytes() == ctx.script_content


@then("the download raises a hash validation error")
def then_hash_validation_error(ctx: DownloadFlowContext) -> None:
    """Verify hash validation error was raised.

    Args:
        ctx: Download flow context.
    """
    assert ctx.error is not None
    assert isinstance(ctx.error, ValueError)
    assert "Hash validation failed" in str(ctx.error)


@then("the cached file is removed")
def then_cached_file_removed(ctx: DownloadFlowContext) -> None:
    """Verify cached file is removed after failed validation.

    Args:
        ctx: Download flow context.
    """
    assert ctx.temp_cache is not None
    cached_path = ctx.temp_cache / "test.rpy"
    assert not cached_path.exists()


@then("the HTTP server is not called")
def then_http_not_called(ctx: DownloadFlowContext) -> None:
    """Verify HTTP server was not called.

    Args:
        ctx: Download flow context.
    """
    assert ctx.mock_route is not None
    assert not ctx.mock_route.called


@then("the cached script is returned")
def then_cached_script_returned(ctx: DownloadFlowContext) -> None:
    """Verify cached script is returned.

    Args:
        ctx: Download flow context.
    """
    assert ctx.results is not None
    assert "test.rpy" in ctx.results
    assert ctx.results["test.rpy"].exists()


@then("each script is downloaded successfully")
def then_each_script_downloaded(ctx: DownloadFlowContext) -> None:
    """Verify each script is downloaded successfully.

    Args:
        ctx: Download flow context.
    """
    assert ctx.results is not None
    assert len(ctx.results) == 2
    assert "script1.rpy" in ctx.results
    assert "script2.rpy" in ctx.results


@then("progress callbacks are invoked in order")
def then_progress_callbacks_invoked(ctx: DownloadFlowContext) -> None:
    """Verify progress callbacks are invoked in order.

    Args:
        ctx: Download flow context.
    """
    assert len(ctx.progress_calls) == 2
    assert ctx.progress_calls[0] == ("script1.rpy", 1, 2)
    assert ctx.progress_calls[1] == ("script2.rpy", 2, 2)


@then("the download raises an HTTP error")
def then_http_error_raised(ctx: DownloadFlowContext) -> None:
    """Verify HTTP error was raised.

    Args:
        ctx: Download flow context.
    """
    assert ctx.error is not None
    assert isinstance(ctx.error, httpx.HTTPStatusError)


@then("the download raises a manifest coverage error")
def then_manifest_coverage_error(ctx: DownloadFlowContext) -> None:
    """Verify manifest coverage error was raised.

    Args:
        ctx: Download flow context.
    """
    assert ctx.error is not None
    assert isinstance(ctx.error, ValueError)
    assert "not found in hash manifest" in str(ctx.error)


@then("the aligned output contains paired source and reference lines")
def then_aligned_output_valid(ctx: DownloadFlowContext) -> None:
    """Verify aligned output contains paired source and reference lines.

    Args:
        ctx: Download flow context.
    """
    # Verify parsing worked
    assert len(ctx.ja_lines) == 2
    assert ctx.ja_lines[0].speaker == "hisao"
    assert len(ctx.en_lines) == 2
    assert ctx.en_lines[0].speaker == "hisao"
    assert ctx.en_lines[0].text == "Hello"

    # Verify alignment
    assert len(ctx.aligned) == 2
    assert ctx.aligned[0].source.speaker == "hisao"
    assert ctx.aligned[0].reference is not None
    assert ctx.aligned[0].reference.text == "Hello"
    assert ctx.aligned[1].source.speaker == "emi"
    assert ctx.aligned[1].reference is not None
    assert ctx.aligned[1].reference.text == "Hey!"


@when("I parse the script with RenpyDialogueParser")
def when_parse_single_script(ctx: DownloadFlowContext) -> None:
    """Parse the downloaded script.

    Args:
        ctx: Download flow context.
    """
    assert ctx.results is not None
    parser = RenpyDialogueParser()
    ctx.parsed_lines = parser.parse_script(ctx.results["test.rpy"])


@when("I serialize the parsed lines to JSONL")
def when_serialize_to_jsonl(ctx: DownloadFlowContext) -> None:
    """Serialize parsed lines to JSONL format excluding source_columns.

    Args:
        ctx: Download flow context.
    """
    assert ctx.temp_cache is not None
    ctx.jsonl_path = ctx.temp_cache / "output.jsonl"

    # Serialize lines excluding source_columns to match benchmark download behavior
    with ctx.jsonl_path.open("w", encoding="utf-8") as f:
        for line in ctx.parsed_lines:
            f.write(
                line.model_dump_json(exclude={"source_columns"}, exclude_none=True)
                + "\n"
            )


@then("the JSONL can be loaded by the ingest adapter")
def then_jsonl_ingestable(ctx: DownloadFlowContext) -> None:
    """Verify JSONL can be loaded by the ingest adapter without errors.

    Args:
        ctx: Download flow context.
    """
    assert ctx.jsonl_path is not None
    assert ctx.jsonl_path.exists()

    # Create IngestSource with correct field names
    source = IngestSource(
        input_path=str(ctx.jsonl_path),
        format=FileFormat.JSONL,
    )

    # Load via JsonlIngestAdapter
    adapter = JsonlIngestAdapter()
    ctx.ingested_lines = asyncio.run(adapter.load_source(source))

    # Verify lines were loaded successfully
    assert len(ctx.ingested_lines) > 0
    assert ctx.ingested_lines[0].line_id == ctx.parsed_lines[0].line_id
    assert ctx.ingested_lines[0].text == ctx.parsed_lines[0].text
