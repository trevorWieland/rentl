"""Integration test: pipeline model construction from config data.

Verifies that PhaseProgress objects can be constructed from config phase
names, which are stored as plain strings due to use_enum_values=True.
This is the exact code path that broke in the DeepSeek pipeline.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from rentl_schemas.config import RunConfig
from rentl_schemas.primitives import PhaseStatus
from rentl_schemas.progress import (
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
)
from rentl_schemas.validation import validate_run_config

_CONFIG_DIR = (
    Path(__file__).resolve().parents[3] / "benchmark" / "karetoshi" / "configs"
)


def _load_config(filename: str) -> RunConfig:
    """Load and validate a pilot config file.

    Returns:
        RunConfig: Validated run configuration.
    """
    config_path = _CONFIG_DIR / filename
    with open(config_path, "rb") as f:
        payload = tomllib.load(f)
    return validate_run_config(payload)


def _config_filenames() -> list[str]:
    """Discover available pilot config files.

    Returns:
        list[str]: Sorted list of config filenames.
    """
    assert _CONFIG_DIR.exists(), f"Config directory missing: {_CONFIG_DIR}"
    filenames = sorted(p.name for p in _CONFIG_DIR.glob("*.toml"))
    assert filenames, f"No .toml configs found in {_CONFIG_DIR}"
    return filenames


@pytest.mark.integration
class TestPipelineConstruction:
    """Test pipeline model construction from real config data."""

    @pytest.mark.parametrize("config_file", _config_filenames())
    def test_build_initial_progress_from_config(self, config_file: str) -> None:
        """Construct PhaseProgress for every enabled phase in config."""
        config = _load_config(config_file)

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
