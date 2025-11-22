"""Logging helpers for rentl."""

from __future__ import annotations

import logging

_LOGGING_INITIALIZED = False


def configure_logging(verbose: bool = False) -> None:
    """Configure the global logger once."""
    global _LOGGING_INITIALIZED
    level = logging.DEBUG if verbose else logging.INFO
    if not _LOGGING_INITIALIZED:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        _LOGGING_INITIALIZED = True
    else:
        logging.getLogger().setLevel(level)

    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for *name*, configuring logging if needed."""
    if not _LOGGING_INITIALIZED:
        configure_logging()
    return logging.getLogger(name)
