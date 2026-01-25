"""CLI entry point - thin adapter over rentl-core."""

import typer
from rich import print as rprint

from rentl_core import VERSION

app = typer.Typer(
    help="Agentic localization pipeline",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Rentl CLI."""


@app.command()
def version() -> None:
    """Display version information."""
    rprint(f"[bold]rentl[/bold] v{VERSION}")


if __name__ == "__main__":
    app()
