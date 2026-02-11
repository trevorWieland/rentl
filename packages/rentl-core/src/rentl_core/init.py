"""Project initialization logic for rentl."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import FileFormat


class ProviderPreset(BaseSchema):
    """Provider preset with pre-filled configuration values."""

    name: str = Field(..., description="Display name of the provider")
    provider_name: str = Field(..., description="Provider identifier for config")
    base_url: str = Field(..., description="OpenAI-compatible endpoint base URL")
    api_key_env: str = Field(..., description="Environment variable name for API key")
    model_id: str = Field(..., description="Default model identifier")


# Provider presets for common LLM providers
PROVIDER_PRESETS: list[ProviderPreset] = [
    ProviderPreset(
        name="OpenRouter",
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4-turbo",
    ),
    ProviderPreset(
        name="OpenAI",
        provider_name="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        model_id="gpt-4.1-turbo",
    ),
    ProviderPreset(
        name="Local (Ollama)",
        provider_name="ollama",
        base_url="http://localhost:11434/v1",
        api_key_env="OLLAMA_API_KEY",
        model_id="llama3",
    ),
]


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
        ..., min_length=1, description="Model identifier (e.g., 'openai/gpt-4-turbo')"
    )
    input_format: FileFormat = Field(
        ...,
        description="Input file format (e.g., 'jsonl', 'csv', 'txt')",
    )
    include_seed_data: bool = Field(
        True, description="Whether to create a seed sample input file"
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base_url is a properly formatted URL.

        Args:
            v: The base_url value to validate.

        Returns:
            str: The validated base_url.

        Raises:
            ValueError: If the base_url is not a valid URL.
        """
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                f"Invalid URL format: '{v}'. Expected a full URL like "
                "'https://api.example.com/v1' or 'http://localhost:11434/v1'"
            )
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme: '{parsed.scheme}'. "
                "Only 'http' and 'https' are supported."
            )
        return v


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
    used_fallback = False
    if answers.include_seed_data:
        seed_path = input_dir / f"{answers.game_name}.{answers.input_format}"
        seed_content, used_fallback = _generate_seed_data(answers)
        seed_path.write_text(seed_content, encoding="utf-8")
        created_files.append(str(seed_path.relative_to(target_dir)))

    # Build next-step instructions
    input_file = f"./input/{answers.game_name}.{answers.input_format}"
    next_steps = [
        f"Set your API key in .env: {answers.api_key_env}=your_key_here",
    ]
    if not answers.include_seed_data:
        next_steps.append(f"Place your input data into {input_file}")
    elif used_fallback:
        next_steps.append(
            f"NOTE: Generated seed data is in English "
            f"(language '{answers.source_language}' not supported). "
            f"Replace the content in {input_file} with text in your "
            f"source language before running the pipeline."
        )
    next_steps.append("Run your first pipeline: rentl run-pipeline")

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


def _get_sample_text(language: str) -> tuple[tuple[str, str, str], bool]:
    """Get sample dialogue text in the specified language.

    Args:
        language: ISO language code (e.g., 'ja', 'en', 'es').

    Returns:
        tuple[tuple[str, str, str], bool]: Three sample dialogue lines
            in the target language, and a boolean indicating whether
            the fallback to English was used.
    """
    # Language-specific sample text
    samples: dict[str, tuple[str, str, str]] = {
        "ja": (
            "サンプル台詞 1",
            "サンプル台詞 2",
            "サンプル台詞 3",
        ),
        "zh": (
            "示例对话 1",
            "示例对话 2",
            "示例对话 3",
        ),
        "ko": (
            "샘플 대사 1",
            "샘플 대사 2",
            "샘플 대사 3",
        ),
        "es": (
            "Línea de diálogo de ejemplo 1",
            "Línea de diálogo de ejemplo 2",
            "Línea de diálogo de ejemplo 3",
        ),
        "fr": (
            "Ligne de dialogue exemple 1",
            "Ligne de dialogue exemple 2",
            "Ligne de dialogue exemple 3",
        ),
        "de": (
            "Beispiel-Dialogzeile 1",
            "Beispiel-Dialogzeile 2",
            "Beispiel-Dialogzeile 3",
        ),
        "en": (
            "Example dialogue line 1",
            "Example dialogue line 2",
            "Example dialogue line 3",
        ),
    }

    # Return language-specific samples or English default, with fallback indicator
    lang_key = language.lower()
    used_fallback = lang_key not in samples
    return samples.get(lang_key, samples["en"]), used_fallback


def _generate_seed_data(answers: InitAnswers) -> tuple[str, bool]:
    """Generate seed sample data in the requested format and source language.

    Args:
        answers: User responses from the init interview.

    Returns:
        tuple[str, bool]: Seed data content in the configured source language,
            and a boolean indicating whether the fallback to English was used.

    Raises:
        ValueError: If the input format is not supported.
    """
    # Get sample text in the source language
    (line1, line2, line3), used_fallback = _get_sample_text(answers.source_language)

    if answers.input_format == FileFormat.JSONL:
        # Generate 3 sample JSONL lines representing one scene
        seed_content = (
            '{"scene_id": "scene_001", "route_id": "route_001", "line_id": "line_001", '
            f'"speaker": "Character A", "text": "{line1}"}}\n'
            '{"scene_id": "scene_001", "route_id": "route_001", "line_id": "line_002", '
            f'"speaker": "Character B", "text": "{line2}"}}\n'
            '{"scene_id": "scene_001", "route_id": "route_001", "line_id": "line_003", '
            f'"speaker": "Character A", "text": "{line3}"}}\n'
        )
        return seed_content, used_fallback
    elif answers.input_format == FileFormat.CSV:
        # CSV format with headers
        seed_content = (
            "scene_id,route_id,line_id,speaker,text\n"
            f"scene_001,route_001,line_001,Character A,{line1}\n"
            f"scene_001,route_001,line_002,Character B,{line2}\n"
            f"scene_001,route_001,line_003,Character A,{line3}\n"
        )
        return seed_content, used_fallback
    elif answers.input_format == FileFormat.TXT:
        # TXT format with simple line-based structure
        seed_content = (
            f"Character A: {line1}\nCharacter B: {line2}\nCharacter A: {line3}\n"
        )
        return seed_content, used_fallback
    else:
        # Exhaustive match - this branch should never execute
        raise ValueError(f"Unsupported file format: {answers.input_format}")
