"""rentl command-line interface."""

import typer

from rentl_cli.commands.run import context, edit, reset_example, status, translate
from rentl_cli.commands.validate import validate

app = typer.Typer(help="rentl - Multi-agent translation pipeline for visual novels")


@app.command()
def version() -> None:
    """Show CLI version."""
    typer.echo("rentl v1.0-dev")


# Core pipeline commands
app.command()(validate)
app.command()(context)
app.command()(translate)
app.command()(edit)
app.command()(status)
app.command("reset-example")(reset_example)


def main() -> None:
    """Entrypoint invoked by ``python -m rentl_cli`` or console scripts."""
    app()


if __name__ == "__main__":
    main()
