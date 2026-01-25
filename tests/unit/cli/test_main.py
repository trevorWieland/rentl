"""Unit tests for rentl-cli."""

from typer.testing import CliRunner

from rentl_cli.main import app

runner = CliRunner()


def test_version_command() -> None:
    """Test version command outputs version string."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
