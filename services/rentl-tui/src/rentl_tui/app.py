"""TUI application - thin adapter over rentl-core."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static

from rentl_core import VERSION


class RentlApp(App):
    """Rentl TUI application."""

    TITLE = "rentl"
    SUB_TITLE = f"v{VERSION}"

    def compose(self) -> ComposeResult:
        """Compose the TUI layout.

        Yields:
             The header and static widgets.
        """
        yield Header()
        yield Static(f"rentl v{VERSION} - Agentic localization pipeline")
        yield Footer()


def main() -> None:
    """Run the TUI application."""
    app = RentlApp()
    app.run()


if __name__ == "__main__":
    main()
