"""Shared CLI typer argument definitions."""

from pathlib import Path
from typing import Annotated

import typer

ProjectPathArgument = Annotated[
    Path,
    typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
]
