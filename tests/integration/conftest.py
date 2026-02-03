"""Integration test configuration with shared BDD fixtures and step definitions."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse

if TYPE_CHECKING:
    from collections.abc import Generator

# Apply integration marker to all tests in this directory
pytestmark = pytest.mark.integration


class FakeLlmRuntime:
    """Mock LLM runtime for integration tests (no real API calls)."""

    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        """Return a fake response without making real API calls."""
        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text="ok",
        )


# --- Pytest fixtures ---


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Typer CLI runner for invoking commands."""
    return CliRunner()


@pytest.fixture
def fake_llm_runtime() -> FakeLlmRuntime:
    """Return a mock LLM runtime for testing without real API calls."""
    return FakeLlmRuntime()


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory.

    Returns:
        Path to the created workspace directory.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def mock_llm_runtime(
    monkeypatch: pytest.MonkeyPatch, fake_llm_runtime: FakeLlmRuntime
) -> Generator[FakeLlmRuntime]:
    """Patch the CLI to use a fake LLM runtime.

    Yields:
        The fake LLM runtime instance.
    """
    monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: fake_llm_runtime)
    yield fake_llm_runtime


@pytest.fixture
def set_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set fake API keys in the environment for testing."""
    monkeypatch.setenv("PRIMARY_KEY", "fake-key")
    monkeypatch.setenv("SECONDARY_KEY", "fake-key")
    monkeypatch.setenv("TERTIARY_KEY", "fake-key")


# --- Helper functions ---


def write_rentl_config(
    config_path: Path,
    workspace_dir: Path,
    *,
    input_format: str = "txt",
    output_format: str = "txt",
    phases: list[str] | None = None,
) -> Path:
    """Write a rentl.toml config file for testing.

    Args:
        config_path: Directory to write the config file in.
        workspace_dir: Workspace directory for the project.
        input_format: Input file format (txt, csv, jsonl).
        output_format: Output file format (txt, csv, jsonl).
        phases: List of phases to include. Defaults to all phases.

    Returns:
        Path to the written config file.
    """
    if phases is None:
        phases = [
            "ingest",
            "context",
            "pretranslation",
            "translate",
            "qa",
            "edit",
            "export",
        ]

    phase_config = "\n".join(f'[[pipeline.phases]]\nphase = "{p}"' for p in phases)

    content = textwrap.dedent(
        f"""\
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "test-project"

        [project.paths]
        workspace_dir = "{workspace_dir}"
        input_path = "input.{input_format}"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "{input_format}"
        output_format = "{output_format}"

        [project.languages]
        source_language = "ja"
        target_languages = ["en"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "http://localhost:8001/v1"
        api_key_env = "PRIMARY_KEY"

        [[endpoints.endpoints]]
        provider_name = "secondary"
        base_url = "http://localhost:8002/v1"
        api_key_env = "SECONDARY_KEY"

        [[endpoints.endpoints]]
        provider_name = "tertiary"
        base_url = "http://localhost:8003/v1"
        api_key_env = "TERTIARY_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "primary"

        {phase_config}

        [concurrency]
        max_parallel_requests = 1
        max_parallel_scenes = 1

        [retry]
        max_retries = 1
        backoff_s = 1.0
        max_backoff_s = 2.0

        [cache]
        enabled = false
        """
    )
    file_path = config_path / "rentl.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path
