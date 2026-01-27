"""Unit tests for rentl-cli."""

import json
from pathlib import Path

from typer.testing import CliRunner

from rentl_cli.main import app

runner = CliRunner()


def test_version_command() -> None:
    """Test version command outputs version string."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_export_command_outputs_warnings(tmp_path: Path) -> None:
    """Export command surfaces warnings in the response."""
    input_path = tmp_path / "translated.jsonl"
    output_path = tmp_path / "output.csv"

    payload = {
        "line_id": "line_1",
        "source_text": "Hello",
        "text": "Hello",
        "metadata": None,
    }
    input_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "export",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "csv",
            "--untranslated-policy",
            "warn",
            "--include-source-text",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"] is None
    assert response["data"]["summary"]["line_count"] == 1
    assert response["data"]["warnings"][0]["code"] == "untranslated_text"
    assert output_path.exists()
