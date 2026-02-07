"""Unit tests for project initialization logic."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from rentl_core.init import InitAnswers, InitResult, generate_project
from rentl_schemas.config import RunConfig


@pytest.fixture
def default_answers() -> InitAnswers:
    """Default answers for testing.

    Returns:
        InitAnswers: Default initialization answers for test cases.
    """
    return InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4.1",
        input_format="jsonl",
        include_seed_data=True,
    )


def test_generate_project_creates_expected_files(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test that generate_project creates all expected files and directories."""
    result = generate_project(default_answers, tmp_path)

    # Verify created files list
    assert "input/" in result.created_files
    assert "out/" in result.created_files
    assert "logs/" in result.created_files
    assert "rentl.toml" in result.created_files
    assert ".env" in result.created_files
    assert "input/seed.jsonl" in result.created_files

    # Verify files actually exist
    assert (tmp_path / "input").is_dir()
    assert (tmp_path / "out").is_dir()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "rentl.toml").is_file()
    assert (tmp_path / ".env").is_file()
    assert (tmp_path / "input" / "seed.jsonl").is_file()


def test_generate_project_produces_next_steps(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test that generate_project returns actionable next steps."""
    result = generate_project(default_answers, tmp_path)

    assert len(result.next_steps) >= 3
    assert any("API key" in step for step in result.next_steps)
    assert any("input data" in step for step in result.next_steps)
    assert any("run-pipeline" in step for step in result.next_steps)


def test_generated_config_is_valid_toml(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test that the generated rentl.toml parses as valid TOML."""
    generate_project(default_answers, tmp_path)
    config_path = tmp_path / "rentl.toml"

    # Should parse without raising
    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)

    # Basic structure checks
    assert "project" in config_dict
    assert "logging" in config_dict
    assert "endpoint" in config_dict
    assert "pipeline" in config_dict
    assert "concurrency" in config_dict
    assert "retry" in config_dict
    assert "cache" in config_dict


def test_generated_config_validates_against_schema(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test that the generated rentl.toml passes RunConfig validation."""
    generate_project(default_answers, tmp_path)
    config_path = tmp_path / "rentl.toml"

    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)

    # Should validate without raising
    config = RunConfig.model_validate(config_dict, strict=True)

    # Verify key fields match answers
    assert config.project.project_name == default_answers.project_name
    assert config.project.languages.source_language == default_answers.source_language
    assert config.project.languages.target_languages == default_answers.target_languages
    assert config.endpoint is not None
    assert config.endpoint.provider_name == default_answers.provider_name
    assert config.endpoint.base_url == default_answers.base_url
    assert config.endpoint.api_key_env == default_answers.api_key_env
    assert config.pipeline.default_model is not None
    assert config.pipeline.default_model.model_id == default_answers.model_id


def test_generated_config_omits_agents_section(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test that the generated config does not include an [agents] section."""
    generate_project(default_answers, tmp_path)
    config_path = tmp_path / "rentl.toml"

    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)

    # Verify [agents] section is not present
    assert "agents" not in config_dict

    # Validate and verify agents field is None
    config = RunConfig.model_validate(config_dict, strict=True)
    assert config.agents is None


def test_generated_env_contains_api_key_placeholder(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test that the .env file contains the correct API key placeholder."""
    generate_project(default_answers, tmp_path)
    env_path = tmp_path / ".env"

    env_content = env_path.read_text(encoding="utf-8")
    assert default_answers.api_key_env in env_content
    assert f"{default_answers.api_key_env}=" in env_content


def test_seed_data_jsonl_format(tmp_path: Path, default_answers: InitAnswers) -> None:
    """Test that seed data is valid JSONL with expected structure."""
    generate_project(default_answers, tmp_path)
    seed_path = tmp_path / "input" / "seed.jsonl"

    lines = seed_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3

    for line in lines:
        data = json.loads(line)
        assert "scene_id" in data
        assert "route_id" in data
        assert "line_id" in data
        assert "speaker" in data
        assert "original_text" in data


def test_seed_data_csv_format(tmp_path: Path) -> None:
    """Test that seed data generates valid CSV when format is csv."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4.1",
        input_format="csv",
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / "seed.csv"

    lines = seed_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 4  # Header + 3 data rows

    # Check header
    header = lines[0]
    assert "scene_id" in header
    assert "speaker" in header
    assert "original_text" in header

    # Check data rows
    for line in lines[1:]:
        assert "scene_001" in line
        assert "Example dialogue line" in line


def test_seed_data_tsv_format(tmp_path: Path) -> None:
    """Test that seed data generates valid TSV when format is tsv."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4.1",
        input_format="tsv",
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / "seed.tsv"

    lines = seed_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 4  # Header + 3 data rows

    # Check header has tabs
    header = lines[0]
    assert "\t" in header
    assert "scene_id" in header

    # Check data rows have tabs
    for line in lines[1:]:
        assert "\t" in line
        assert "scene_001" in line


def test_generate_project_without_seed_data(tmp_path: Path) -> None:
    """Test that seed data is not created when include_seed_data=False."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4.1",
        input_format="jsonl",
        include_seed_data=False,
    )

    result = generate_project(answers, tmp_path)

    # Verify seed file not in created files
    assert not any("seed" in f for f in result.created_files)

    # Verify seed file does not exist
    seed_path = tmp_path / "input" / "seed.jsonl"
    assert not seed_path.exists()


def test_generate_project_with_multiple_target_languages(tmp_path: Path) -> None:
    """Test config generation with multiple target languages."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en", "es", "fr"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4.1",
        input_format="jsonl",
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    config_path = tmp_path / "rentl.toml"

    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)

    config = RunConfig.model_validate(config_dict, strict=True)
    assert config.project.languages.target_languages == ["en", "es", "fr"]


def test_init_answers_validation() -> None:
    """Test that InitAnswers validates constraints."""
    # Valid answers should not raise
    InitAnswers(
        project_name="test",
        game_name="test",
        source_language="ja",
        target_languages=["en"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="KEY",
        model_id="model",
        input_format="jsonl",
        include_seed_data=True,
    )

    # Empty project_name should raise
    with pytest.raises(ValueError):
        InitAnswers(
            project_name="",
            game_name="test",
            source_language="ja",
            target_languages=["en"],
            provider_name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="KEY",
            model_id="model",
            input_format="jsonl",
            include_seed_data=True,
        )

    # Empty target_languages should raise
    with pytest.raises(ValueError):
        InitAnswers(
            project_name="test",
            game_name="test",
            source_language="ja",
            target_languages=[],
            provider_name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="KEY",
            model_id="model",
            input_format="jsonl",
            include_seed_data=True,
        )


def test_init_result_structure() -> None:
    """Test InitResult structure and validation."""
    result = InitResult(
        created_files=["rentl.toml", ".env", "input/"],
        next_steps=["Step 1", "Step 2"],
    )

    assert len(result.created_files) == 3
    assert len(result.next_steps) == 2
