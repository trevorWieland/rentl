"""Project initialization logic for rentl."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import FileFormat


class InitAnswers(BaseSchema):
    """User responses from the init interview."""

    project_name: str = Field(
        ..., min_length=1, description="Project name for the pipeline run"
    )
    game_name: str = Field(
        ..., min_length=1, description="Name of the game to translate"
    )
    source_language: str = Field(
        ..., min_length=2, max_length=3, description="Source language code (e.g., 'ja')"
    )
    target_languages: list[str] = Field(
        ..., min_length=1, description="Target language codes (e.g., ['en'])"
    )
    provider_name: str = Field(
        ..., min_length=1, description="Endpoint provider name (e.g., 'openrouter')"
    )
    base_url: str = Field(
        ..., min_length=1, description="OpenAI-compatible endpoint base URL"
    )
    api_key_env: str = Field(
        ...,
        min_length=1,
        description=(
            "Environment variable name for API key (e.g., 'OPENROUTER_API_KEY')"
        ),
    )
    model_id: str = Field(
        ..., min_length=1, description="Model identifier (e.g., 'openai/gpt-4.1')"
    )
    input_format: FileFormat = Field(
        ...,
        description="Input file format (e.g., 'jsonl', 'csv', 'txt')",
    )
    include_seed_data: bool = Field(
        True, description="Whether to create a seed sample input file"
    )


class InitResult(BaseSchema):
    """Results from project generation."""

    created_files: list[str] = Field(
        ..., description="List of file paths created during init"
    )
    next_steps: list[str] = Field(
        ..., description="Instructions for the user to complete setup"
    )


def generate_project(answers: InitAnswers, target_dir: Path) -> InitResult:
    """Generate a ready-to-run rentl project from interview answers.

    Args:
        answers: User responses from the init interview.
        target_dir: Directory where project files will be created.

    Returns:
        InitResult: Metadata about created files and next steps.
    """
    created_files: list[str] = []

    # Create workspace directories
    input_dir = target_dir / "input"
    output_dir = target_dir / "out"
    logs_dir = target_dir / "logs"

    for directory in [input_dir, output_dir, logs_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        created_files.append(str(directory.relative_to(target_dir)) + "/")

    # Generate rentl.toml
    config_path = target_dir / "rentl.toml"
    toml_content = _generate_toml(answers)
    config_path.write_text(toml_content, encoding="utf-8")
    created_files.append(str(config_path.relative_to(target_dir)))

    # Generate .env template
    env_path = target_dir / ".env"
    env_content = _generate_env(answers)
    env_path.write_text(env_content, encoding="utf-8")
    created_files.append(str(env_path.relative_to(target_dir)))

    # Generate seed data if requested
    if answers.include_seed_data:
        seed_path = input_dir / f"seed.{answers.input_format}"
        seed_content = _generate_seed_data(answers)
        seed_path.write_text(seed_content, encoding="utf-8")
        created_files.append(str(seed_path.relative_to(target_dir)))

    # Build next-step instructions
    input_file = f"./input/{answers.game_name}.{answers.input_format}"
    next_steps = [
        f"Set your API key in .env: {answers.api_key_env}=your_key_here",
        f"Place your input data into {input_file}",
        "Run your first pipeline: rentl run-pipeline",
    ]

    return InitResult(created_files=created_files, next_steps=next_steps)


def _generate_toml(answers: InitAnswers) -> str:
    """Generate a valid rentl.toml config from answers.

    Args:
        answers: User responses from the init interview.

    Returns:
        str: TOML configuration content.
    """
    # Join target languages as comma-separated strings for TOML array
    target_langs = ", ".join(f'"{lang}"' for lang in answers.target_languages)

    return f'''[project]
schema_version = {{ major = 0, minor = 1, patch = 0 }}
project_name = "{answers.project_name}"

[project.paths]
workspace_dir = "."
input_path = "./input/{answers.game_name}.{answers.input_format}"
output_dir = "./out"
logs_dir = "./logs"

[project.formats]
input_format = "{answers.input_format}"
output_format = "{answers.input_format}"

[project.languages]
source_language = "{answers.source_language}"
target_languages = [{target_langs}]

[logging]
sinks = [
    {{ type = "console" }},
    {{ type = "file" }},
]

[endpoint]
provider_name = "{answers.provider_name}"
base_url = "{answers.base_url}"
api_key_env = "{answers.api_key_env}"

[pipeline]

[pipeline.default_model]
model_id = "{answers.model_id}"

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

[concurrency]
max_parallel_requests = 8
max_parallel_scenes = 4

[retry]
max_retries = 3
backoff_s = 1.0
max_backoff_s = 30.0

[cache]
enabled = false
'''


def _generate_env(answers: InitAnswers) -> str:
    """Generate a .env template with API key placeholder.

    Args:
        answers: User responses from the init interview.

    Returns:
        str: .env file content.
    """
    return f"# Set your API key for {answers.provider_name}\n{answers.api_key_env}=\n"


def _generate_seed_data(answers: InitAnswers) -> str:
    """Generate seed sample data in the requested format.

    Args:
        answers: User responses from the init interview.

    Returns:
        str: Seed data content.

    Raises:
        ValueError: If the input format is not supported.
    """
    if answers.input_format == FileFormat.JSONL:
        # Generate 3 sample JSONL lines representing one scene
        return (
            '{"scene_id": "scene_001", "route_id": "route_001", "line_id": "line_001", '
            '"speaker": "Character A", "text": "Example dialogue line 1"}\n'
            '{"scene_id": "scene_001", "route_id": "route_001", "line_id": "line_002", '
            '"speaker": "Character B", "text": "Example dialogue line 2"}\n'
            '{"scene_id": "scene_001", "route_id": "route_001", "line_id": "line_003", '
            '"speaker": "Character A", "text": "Example dialogue line 3"}\n'
        )
    elif answers.input_format == FileFormat.CSV:
        # CSV format with headers
        return (
            "scene_id,route_id,line_id,speaker,text\n"
            "scene_001,route_001,line_001,Character A,Example dialogue line 1\n"
            "scene_001,route_001,line_002,Character B,Example dialogue line 2\n"
            "scene_001,route_001,line_003,Character A,Example dialogue line 3\n"
        )
    elif answers.input_format == FileFormat.TXT:
        # TXT format with simple line-based structure
        return (
            "Character A: Example dialogue line 1\n"
            "Character B: Example dialogue line 2\n"
            "Character A: Example dialogue line 3\n"
        )
    else:
        # Exhaustive match - this branch should never execute
        raise ValueError(f"Unsupported file format: {answers.input_format}")
