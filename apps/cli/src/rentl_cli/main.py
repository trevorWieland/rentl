"""rentl command-line interface."""

import typer

from rentl_cli.commands.validate import validate

app = typer.Typer(help="rentl CLI entrypoint placeholder")


@app.command()
def version() -> None:
    """Show CLI placeholder version."""
    typer.echo("rentl CLI scaffold")


app.command()(validate)


def main() -> None:
    """Entrypoint invoked by ``python -m rentl_cli`` or console scripts."""
    app()


if __name__ == "__main__":
    main()
