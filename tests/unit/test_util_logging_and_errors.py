"""Tests for rentl_core.util logging setup and errors helper."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import rentl_core.util.logging as logging_util
from rentl_core.util.errors import RentlError
from rentl_core.util.logging import configure_logging


def test_configure_logging_creates_file_and_sets_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """configure_logging should set root level and create the log file."""
    log_path = tmp_path / "test.log"

    # Reset logging module state for the test
    monkeypatch.setattr(logging_util, "_LOGGING_INITIALIZED", False)
    root = logging.getLogger()
    root.handlers.clear()

    configure_logging("debug", log_path)

    logger = logging.getLogger()
    assert logger.level == logging.DEBUG
    assert log_path.exists()


def test_error_helper_returns_message() -> None:
    """RentlError should behave as a simple Exception subclass."""
    err = RentlError("boom")
    assert isinstance(err, Exception)
    assert str(err) == "boom"
