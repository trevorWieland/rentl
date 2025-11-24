"""rentl command-line interface."""

import typer

from rentl_cli.commands.run import context, detail_mvp, detail_scene, edit, reset_example, translate
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
app.command("reset-example")(reset_example)

# Development/debugging commands
app.command("detail-scene")(detail_scene)
app.command("detail-mvp")(detail_mvp)


def main() -> None:
    """Entrypoint invoked by ``python -m rentl_cli`` or console scripts."""
    app()


if __name__ == "__main__":
    main()
