"""Integration test: pipeline model construction from config data.

Verifies that PhaseProgress objects can be constructed from config phase
names, which are stored as plain strings due to use_enum_values=True.
This is the exact code path that broke in the DeepSeek pipeline.
"""

from __future__ import annotations

import textwrap
import tomllib

import pytest

from rentl_schemas.primitives import PhaseStatus
from rentl_schemas.progress import (
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
)
from rentl_schemas.validation import validate_run_config

# Phase sets to test against
_CONFIGS: list[tuple[str, list[str]]] = [
    (
        "all_llm_phases",
        ["ingest", "context", "pretranslation", "translate", "qa", "edit", "export"],
    ),
    (
        "io_only",
        ["ingest", "export"],
    ),
]

_AGENT_MAP = {
    "context": "context_agent",
    "pretranslation": "pretranslation_agent",
    "translate": "translate_agent",
    "qa": "qa_agent",
    "edit": "edit_agent",
}


def _build_config_toml(phases: list[str]) -> str:
    """Generate a minimal valid TOML config string for the given phases.

    Returns:
        str: A valid TOML config string.
    """
    phase_entries: list[str] = []
    for phase in phases:
        entry = f'[[pipeline.phases]]\nphase = "{phase}"'
        agent_name = _AGENT_MAP.get(phase)
        if agent_name:
            entry += f'\nagents = ["{agent_name}"]'
        phase_entries.append(entry)
    phase_block = "\n".join(phase_entries)

    return textwrap.dedent(f"""\
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "test-project"

        [project.paths]
        workspace_dir = "/tmp/test-workspace"
        input_path = "input.txt"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "txt"
        output_format = "txt"

        [project.languages]
        source_language = "ja"
        target_languages = ["en"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [agents]
        prompts_dir = "/tmp/test-workspace/prompts"
        agents_dir = "/tmp/test-workspace/agents"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "http://localhost:8001/v1"
        api_key_env = "PRIMARY_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "primary"

        {phase_block}

        [concurrency]
        max_parallel_requests = 1
        max_parallel_scenes = 1

        [retry]
        max_retries = 1
        backoff_s = 1.0
        max_backoff_s = 2.0

        [cache]
        enabled = false
    """)


@pytest.mark.integration
class TestPipelineConstruction:
    """Test pipeline model construction from inline config data."""

    @pytest.mark.parametrize(
        "label",
        [label for label, _ in _CONFIGS],
        ids=[label for label, _ in _CONFIGS],
    )
    def test_build_initial_progress_from_config(self, label: str) -> None:
        """Construct PhaseProgress for every enabled phase in config."""
        phases = dict(_CONFIGS)[label]
        toml_str = _build_config_toml(phases)
        payload = tomllib.loads(toml_str)
        config = validate_run_config(payload)

        for phase_config in config.pipeline.phases:
            if not phase_config.enabled:
                continue
            # phase_config.phase is a plain string due to use_enum_values=True
            progress = PhaseProgress(
                phase=phase_config.phase,
                status=PhaseStatus.PENDING,
                summary=ProgressSummary(
                    percent_complete=None,
                    percent_mode=ProgressPercentMode.UNAVAILABLE,
                ),
            )
            assert progress.phase == phase_config.phase
