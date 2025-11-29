"""Fallback entrypoint for `python -m rentl`.

Routes to the rentl_cli Typer application.
"""

from rentl_cli.main import main

if __name__ == "__main__":
    main()
