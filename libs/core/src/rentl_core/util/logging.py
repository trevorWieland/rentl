"""Logging helpers for rentl."""

from __future__ import annotations

import logging
from pathlib import Path

_LOGGING_INITIALIZED = False


def configure_logging(verbosity: str = "info", log_file: Path | None = None) -> None:
    """Configure global logging with console and optional file handlers.

    Args:
        verbosity: Logging verbosity for stdout (info, verbose, debug).
        log_file: Optional path for a debug-level log file.
    """
    global _LOGGING_INITIALIZED

    verbosity = verbosity.lower()
    level_map = {"info": logging.INFO, "verbose": logging.DEBUG, "debug": logging.DEBUG}
    console_level = level_map.get(verbosity, logging.INFO)

    root = logging.getLogger()
    if not _LOGGING_INITIALIZED:
        root.setLevel(logging.DEBUG)
        root.handlers.clear()

        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)

        _LOGGING_INITIALIZED = True
    else:
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(console_level)
        if log_file and not any(isinstance(h, logging.FileHandler) for h in root.handlers):
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)

    # Keep noisy libraries at a reasonable level even in verbose mode to avoid flooding logs.
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("rentl_agents").setLevel(logging.INFO)
    logging.getLogger("rentl_pipelines").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for *name*, configuring logging if needed."""
    if not _LOGGING_INITIALIZED:
        configure_logging()
    return logging.getLogger(name)
