"""Integration test configuration with shared BDD fixtures and step definitions."""

from __future__ import annotations

import asyncio
import re
import textwrap
from collections.abc import Awaitable, Callable, Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel
from typer.testing import CliRunner

from rentl_agents.runtime import ProfileAgent
from rentl_llm.openai_runtime import OpenAICompatibleRuntime
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse
from rentl_schemas.phases import (
    IdiomAnnotation,
    IdiomAnnotationList,
    IdiomReviewLine,
    SceneSummary,
    StyleGuideReviewLine,
    StyleGuideReviewList,
    TranslationResultLine,
    TranslationResultList,
)

if TYPE_CHECKING:
    pass

# Apply integration marker to all tests in this directory
pytestmark = pytest.mark.integration


class FakeLlmRuntime:
    """Mock LLM runtime for integration tests (no real API calls)."""

    def __init__(self) -> None:
        """Initialize with call counter."""
        self.call_count = 0

    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        """Return a fake response without making real API calls.

        Returns schema-valid outputs based on the agent being called.
        Detects agent type from prompt content.
        """
        self.call_count += 1
        prompt = request.prompt.lower()

        # Extract scene_id and line_id from prompt if present
        scene_id = "scene_001"
        line_id = "line_001"
        if "scene id:" in prompt:
            # Try to extract actual scene_id from prompt
            for line in request.prompt.split("\n"):
                if "scene id:" in line.lower():
                    parts = line.split(":")
                    if len(parts) > 1:
                        scene_id = parts[1].strip().split()[0]
                    break
        if "line_id" in prompt:
            # Try to extract actual line_id from prompt
            match = re.search(r'"line_id":\s*"([^"]+)"', request.prompt)
            if match:
                line_id = match.group(1)

        # Detect agent type and return appropriate schema-valid output
        if "scene summarization" in prompt or "scene summary" in prompt:
            # SceneSummary schema for scene_summarizer agent
            output_text = f"""{{
  "scene_id": "{scene_id}",
  "summary": "Test scene summary for integration testing.",
  "characters": ["Character A", "Character B"]
}}"""
        elif "idiom" in prompt or "pretranslation" in prompt:
            # IdiomAnnotationList schema for idiom_labeler agent (per-line wrapper)
            output_text = f"""{{
  "reviews": [
    {{
      "line_id": "{line_id}",
      "idioms": [
        {{
          "idiom_text": "test idiom",
          "explanation": "Test idiom explanation for integration testing."
        }}
      ]
    }}
  ]
}}"""
        elif (
            "translate" in prompt
            and "translation" in prompt
            and "style guide" not in prompt
        ):
            # TranslationResultList schema for direct_translator agent
            output_text = f"""{{
  "translations": [
    {{
      "line_id": "{line_id}",
      "text": "Translated test text."
    }}
  ]
}}"""
        elif "style guide" in prompt or "qa" in prompt:
            # StyleGuideReviewList schema for style_guide_critic agent
            output_text = f"""{{
  "reviews": [
    {{
      "line_id": "{line_id}",
      "violations": []
    }}
  ]
}}"""
        elif "edit" in prompt:
            # TranslationResultLine schema for basic_editor agent
            output_text = f"""{{
  "line_id": "{line_id}",
  "text": "Edited test text."
}}"""
        else:
            # Fallback for unknown agents
            output_text = '{"status": "ok"}'

        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text=output_text,
        )


def make_mock_agent_run() -> tuple[
    Callable[[ProfileAgent, BaseModel], Awaitable[BaseModel]],
    dict[str, int],
    dict[str, int],
]:
    """Create a mock_agent_run function with its own counters.

    Returns:
        Tuple of (mock_agent_run function, call_count dict, edit_line_index dict).
    """
    mock_call_count: dict[str, int] = {"count": 0}
    edit_line_index: dict[str, int] = {"index": 0}

    async def mock_agent_run(self: ProfileAgent, payload: BaseModel) -> BaseModel:
        """Return schema-valid output based on agent's output_type.

        For batch operations, returns outputs matching all input IDs to satisfy
        the pipeline's alignment requirements.

        Args:
            self: ProfileAgent instance (patched method).
            payload: Input payload for the agent (phase-specific schema).

        Returns:
            Schema-valid output matching the agent's output_type.

        Raises:
            ValueError: If the agent's output_type is unexpected.
        """
        await asyncio.sleep(0)
        mock_call_count["count"] += 1

        output_type = self._output_type

        if output_type == SceneSummary:
            scene_id = getattr(payload, "scene_id", "scene_001")
            return SceneSummary(
                scene_id=scene_id,
                summary="Test scene summary from mock agent",
                characters=["Character A", "Character B"],
            )
        elif output_type == IdiomAnnotationList:
            source_lines = getattr(payload, "source_lines", [])
            reviews = [
                IdiomReviewLine(
                    line_id=line.line_id,
                    idioms=[
                        IdiomAnnotation(
                            idiom_text="test idiom",
                            explanation="Test explanation",
                        )
                    ],
                )
                for line in source_lines
            ]
            return IdiomAnnotationList(reviews=reviews)
        elif output_type == TranslationResultList:
            source_lines = getattr(payload, "source_lines", [])
            if not source_lines:
                translations = [
                    TranslationResultLine(
                        line_id="line_001",
                        text="Test translation",
                    )
                ]
            else:
                translations = [
                    TranslationResultLine(
                        line_id=line.line_id,
                        text=f"Test translation for {line.line_id}",
                    )
                    for line in source_lines
                ]
            return TranslationResultList(translations=translations)
        elif output_type == StyleGuideReviewList:
            translation_results = getattr(payload, "translation_results", [])
            reviews = [
                StyleGuideReviewLine(
                    line_id=result.line_id,
                    violations=[],
                )
                for result in translation_results
            ]
            return StyleGuideReviewList(reviews=reviews)
        elif output_type == TranslationResultLine:
            translated_lines = getattr(payload, "translated_lines", [])
            if not translated_lines:
                line_id = getattr(payload, "line_id", "line_001")
            else:
                current_index = edit_line_index["index"] % len(translated_lines)
                line_id = translated_lines[current_index].line_id
                edit_line_index["index"] += 1

            return TranslationResultLine(
                line_id=line_id,
                text="Final edited translation",
            )
        else:
            raise ValueError(f"Unexpected output type in test mock: {output_type}")

    return mock_agent_run, mock_call_count, edit_line_index


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
    """Patch OpenAICompatibleRuntime.run_prompt at the execution boundary.

    Mocks at the agent boundary (run_prompt) instead of internal
    factory functions.

    Yields:
        The fake LLM runtime instance.
    """
    monkeypatch.setattr(
        OpenAICompatibleRuntime, "run_prompt", fake_llm_runtime.run_prompt
    )
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

    agent_map = {
        "context": "context_agent",
        "pretranslation": "pretranslation_agent",
        "translate": "translate_agent",
        "qa": "qa_agent",
        "edit": "edit_agent",
    }
    phase_entries: list[str] = []
    for phase in phases:
        entry = f'[[pipeline.phases]]\nphase = "{phase}"'
        agent_name = agent_map.get(phase)
        if agent_name:
            entry += f'\nagents = ["{agent_name}"]'
        phase_entries.append(entry)
    phase_config = "\n".join(phase_entries)

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

        [agents]
        prompts_dir = "{workspace_dir}/prompts"
        agents_dir = "{workspace_dir}/agents"

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
