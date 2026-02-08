"""Quality test configuration with shared fixtures."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

# Apply quality marker to all tests in this directory
pytestmark = pytest.mark.quality


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Typer CLI runner for invoking commands."""
    return CliRunner()
