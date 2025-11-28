"""Shared CLI typer argument definitions."""

from pathlib import Path
from typing import Annotated

import typer

ProjectPathOption = Annotated[
    Path,
    typer.Option(
        "--project-path",
        "-p",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Path to the game project (default: current directory).",
    ),
]
