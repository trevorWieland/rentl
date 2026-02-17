"""Debug script for validating CLI pipeline with temp config."""

from __future__ import annotations

import os
import tempfile
import textwrap
from pathlib import Path

from typer.testing import CliRunner

from rentl.main import app

runner = CliRunner()


def write_multi_endpoint_config(
    config_dir: Path,
    workspace_dir: Path,
) -> Path:
    """Write a temporary rentl.toml for manual validation.

    Args:
        config_dir: Directory to write the config file.
        workspace_dir: Workspace root for resolving relative paths.

    Returns:
        Path to the config file.
    """
    config_path = config_dir / "rentl.toml"
    content = textwrap.dedent(
        f"""
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "debug-run"

        [project.paths]
        workspace_dir = "{workspace_dir}"
        input_path = "samples/golden/script.jsonl"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "jsonl"
        output_format = "jsonl"

        [project.languages]
        source_language = "ja"
        target_languages = ["en"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [[logging.sinks]]
        type = "console"

        [agents]
        prompts_dir = "packages/rentl-agents/prompts"
        agents_dir = "packages/rentl-agents/agents"

        [endpoint]
        provider_name = "local"
        base_url = "http://localhost:1234/v1"
        api_key_env = "RENTL_LOCAL_API_KEY"

        [pipeline.default_model]
        model_id = "openai/gpt-oss-20b"

        [[pipeline.phases]]
        phase = "ingest"

        [[pipeline.phases]]
        phase = "context"
        agents = ["scene_summarizer"]

        [[pipeline.phases]]
        phase = "pretranslation"
        agents = ["idiom_labeler"]

        [[pipeline.phases]]
        phase = "translate"
        agents = ["direct_translator"]

        [[pipeline.phases]]
        phase = "qa"
        agents = ["style_guide_critic"]

        [[pipeline.phases]]
        phase = "edit"
        agents = ["basic_editor"]

        [[pipeline.phases]]
        phase = "export"

        [concurrency]
        max_parallel_requests = 1
        max_parallel_scenes = 1

        [retry]
        max_retries = 1
        backoff_s = 1.0
        max_backoff_s = 2.0

        [cache]
        enabled = false
        """
    ).strip()
    config_path.write_text(content + "\n", encoding="utf-8")
    return config_path


def main() -> None:
    """Run a debug pipeline invocation."""
    if "SECONDARY_KEY" in os.environ:
        del os.environ["SECONDARY_KEY"]

    repo_root = Path(__file__).resolve().parent

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_path = write_multi_endpoint_config(tmp_path, repo_root)

        print(f"Config path: {config_path}")
        print(f"Config exists: {config_path.exists()}")
        print(f"Config content:\n{config_path.read_text()}")

        result = runner.invoke(app, ["run-pipeline", "--config", str(config_path)])

        print(f"Exit code: {result.exit_code}")
        print(f"Stdout: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        if result.exception:
            print(f"Exception: {result.exception}")


if __name__ == "__main__":
    main()
