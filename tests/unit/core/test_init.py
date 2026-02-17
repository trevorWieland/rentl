"""Unit tests for project initialization logic."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from rentl_agents.providers import detect_provider
from rentl_core.init import (
    ENDPOINT_PRESETS,
    InitAnswers,
    InitResult,
    StandardEnvVar,
    generate_project,
)
from rentl_schemas.config import RunConfig
from rentl_schemas.primitives import FileFormat


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
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
        provider_name="OpenRouter",
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
    assert "input/test_game.jsonl" in result.created_files

    # Verify files actually exist
    assert (tmp_path / "input").is_dir()
    assert (tmp_path / "out").is_dir()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "rentl.toml").is_file()
    assert (tmp_path / ".env").is_file()
    assert (tmp_path / "input" / "test_game.jsonl").is_file()


def test_generate_project_produces_next_steps(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test that generate_project returns actionable next steps."""
    result = generate_project(default_answers, tmp_path)

    assert len(result.next_steps) >= 2
    assert any("API key" in step for step in result.next_steps)
    # With include_seed_data=True, "input data" step should NOT be present
    assert not any("Place your input data" in step for step in result.next_steps)
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
    # provider_name is auto-detected from base_url
    assert config.endpoint.base_url == default_answers.base_url
    assert config.endpoint.provider_name == "OpenRouter"  # detected from base_url
    # api_key_env uses standardized name
    assert config.endpoint.api_key_env == StandardEnvVar.API_KEY.value
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
    # Should use standardized env var name
    assert StandardEnvVar.API_KEY.value in env_content
    assert f"{StandardEnvVar.API_KEY.value}=" in env_content


def test_seed_data_jsonl_format(tmp_path: Path, default_answers: InitAnswers) -> None:
    """Test that seed data is valid JSONL with expected structure."""
    generate_project(default_answers, tmp_path)
    seed_path = tmp_path / "input" / f"{default_answers.game_name}.jsonl"

    lines = seed_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3

    for line in lines:
        data = json.loads(line)
        assert "scene_id" in data
        assert "route_id" in data
        assert "line_id" in data
        assert "speaker" in data
        assert "text" in data


def test_seed_data_csv_format(tmp_path: Path) -> None:
    """Test that seed data generates valid CSV when format is csv."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.CSV,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.csv"

    lines = seed_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 4  # Header + 3 data rows

    # Check header
    header = lines[0]
    assert "scene_id" in header
    assert "speaker" in header
    assert "text" in header

    # Check data rows
    for line in lines[1:]:
        assert "scene_001" in line
        # Verify Japanese seed data (not English)
        assert "サンプル台詞" in line


def test_seed_data_txt_format(tmp_path: Path) -> None:
    """Test that seed data generates valid TXT when format is txt."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.TXT,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.txt"

    lines = seed_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3  # 3 dialogue lines

    # Check simple text format
    for line in lines:
        assert ":" in line
        # Verify Japanese seed data (not English)
        assert "サンプル台詞" in line


def test_generate_project_without_seed_data(tmp_path: Path) -> None:
    """Test that seed data is not created when include_seed_data=False."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=False,
    )

    result = generate_project(answers, tmp_path)

    # Verify seed file not in created files
    assert not any(f"{answers.game_name}.jsonl" in f for f in result.created_files)

    # Verify seed file does not exist
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"
    assert not seed_path.exists()

    # Verify "Place your input data" step IS present when seed data not included
    assert any("Place your input data" in step for step in result.next_steps)


def test_generate_project_with_multiple_target_languages(tmp_path: Path) -> None:
    """Test config generation with multiple target languages."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en", "es", "fr"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
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
        base_url="https://openrouter.ai/api/v1",
        model_id="model",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    # Empty project_name should raise
    with pytest.raises(ValueError):
        InitAnswers(
            project_name="",
            game_name="test",
            source_language="ja",
            target_languages=["en"],
            base_url="https://openrouter.ai/api/v1",
            model_id="model",
            input_format=FileFormat.JSONL,
            include_seed_data=True,
        )

    # Empty target_languages should raise
    with pytest.raises(ValueError):
        InitAnswers(
            project_name="test",
            game_name="test",
            source_language="ja",
            target_languages=[],
            base_url="https://openrouter.ai/api/v1",
            model_id="model",
            input_format=FileFormat.JSONL,
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


def test_unsupported_format_rejected() -> None:
    """Test that unsupported formats are rejected at schema validation."""
    # Unsupported format like 'tsv' should raise ValidationError
    with pytest.raises(ValueError, match="Input should be"):
        InitAnswers(
            project_name="test_project",
            game_name="test_game",
            source_language="ja",
            target_languages=["en"],
            base_url="https://openrouter.ai/api/v1",
            model_id="qwen/qwen3-30b-a3b",
            input_format="tsv",  # type: ignore[arg-type]
            include_seed_data=True,
        )


def test_generated_config_uses_correct_agent_names(
    tmp_path: Path, default_answers: InitAnswers
) -> None:
    """Test generated config uses correct default agent names."""
    generate_project(default_answers, tmp_path)
    config_path = tmp_path / "rentl.toml"

    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)

    # Validate config first
    config = RunConfig.model_validate(config_dict, strict=True)

    # Verify pipeline phases exist and use correct agent names
    assert config.pipeline.phases is not None
    phases = {phase.phase: phase.agents for phase in config.pipeline.phases}

    # Check ingest and export phases exist
    assert "ingest" in phases
    assert phases.get("ingest") is None or phases.get("ingest") == []

    # Check correct agent names from default agent pool
    assert phases.get("context") == ["scene_summarizer"]
    assert phases.get("pretranslation") == ["idiom_labeler"]
    assert phases.get("translate") == ["direct_translator"]
    assert phases.get("qa") == ["style_guide_critic"]
    assert phases.get("edit") == ["basic_editor"]

    # Check export phase exists
    assert "export" in phases
    assert phases.get("export") is None or phases.get("export") == []


def test_endpoint_presets_exist() -> None:
    """Test that endpoint presets are defined and contain expected endpoints."""
    assert len(ENDPOINT_PRESETS) >= 3, "Expected at least 3 endpoint presets"

    # Verify expected endpoints are present
    endpoint_names = [preset.name for preset in ENDPOINT_PRESETS]
    assert "OpenRouter" in endpoint_names
    assert "OpenAI" in endpoint_names
    assert "Local" in endpoint_names


def test_endpoint_presets_have_required_fields() -> None:
    """Test that all endpoint presets have complete field values."""
    for preset in ENDPOINT_PRESETS:
        assert preset.name, f"Preset missing name: {preset}"
        assert preset.base_url, f"Preset {preset.name} missing base_url"

        # Verify base_url is a valid URL
        assert preset.base_url.startswith(("http://", "https://")), (
            f"Preset {preset.name} has invalid base_url: {preset.base_url}"
        )


def test_endpoint_preset_creates_valid_config(tmp_path: Path) -> None:
    """Test that each endpoint preset with a default model produces a valid config."""
    for preset in ENDPOINT_PRESETS:
        if preset.default_model is None:
            continue  # Local preset has no default; CLI prompts user
        # Create answers using preset values
        answers = InitAnswers(
            project_name="test_project",
            game_name="test_game",
            source_language="ja",
            target_languages=["en"],
            base_url=preset.base_url,
            model_id=preset.default_model,
            input_format=FileFormat.JSONL,
            include_seed_data=True,
            provider_name=detect_provider(preset.base_url).name,
        )

        # Generate project in a preset-specific subdirectory
        preset_dir = tmp_path / preset.name.replace(" ", "_").replace("(", "").replace(
            ")", ""
        )
        preset_dir.mkdir()
        generate_project(answers, preset_dir)

        # Verify config validates
        config_path = preset_dir / "rentl.toml"
        with config_path.open("rb") as f:
            config_dict = tomllib.load(f)

        config = RunConfig.model_validate(config_dict, strict=True)
        assert config.endpoint is not None
        # provider_name is auto-detected from base_url
        assert config.endpoint.base_url == preset.base_url
        assert isinstance(config.endpoint.provider_name, str)
        assert config.endpoint.provider_name  # not empty
        # api_key_env uses standardized name
        assert config.endpoint.api_key_env == StandardEnvVar.API_KEY.value


def test_base_url_validation_rejects_invalid_urls() -> None:
    """Test that InitAnswers rejects invalid base_url formats."""
    # Non-URL strings should be rejected (with ValueError for format issues)
    invalid_urls_value_error = [
        "not-a-url",
        "just-text",
        "ftp://invalid-scheme.com",  # Unsupported scheme
        "//missing-scheme.com",
    ]

    for invalid_url in invalid_urls_value_error:
        with pytest.raises(ValueError, match="Invalid URL"):
            InitAnswers(
                project_name="test_project",
                game_name="test_game",
                source_language="ja",
                target_languages=["en"],
                base_url=invalid_url,
                model_id="test-model",
                input_format=FileFormat.JSONL,
                include_seed_data=True,
            )

    # Empty string hits min_length constraint (ValidationError, not ValueError)
    with pytest.raises(ValidationError):
        InitAnswers(
            project_name="test_project",
            game_name="test_game",
            source_language="ja",
            target_languages=["en"],
            base_url="",
            model_id="test-model",
            input_format=FileFormat.JSONL,
            include_seed_data=True,
        )


def test_base_url_validation_accepts_valid_urls() -> None:
    """Test that InitAnswers accepts valid base_url formats."""
    valid_urls = [
        "https://api.openai.com/v1",
        "https://openrouter.ai/api/v1",
        "http://localhost:11434/v1",
        "http://127.0.0.1:8080/api",
        "https://custom-domain.example.com/endpoint",
    ]

    for valid_url in valid_urls:
        # Should not raise
        answers = InitAnswers(
            project_name="test_project",
            game_name="test_game",
            source_language="ja",
            target_languages=["en"],
            base_url=valid_url,
            model_id="test-model",
            input_format=FileFormat.JSONL,
            include_seed_data=True,
        )
        assert answers.base_url == valid_url


def test_seed_data_matches_source_language_japanese(tmp_path: Path) -> None:
    """Test that seed data is generated in Japanese when source_language is ja."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ja",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    result = generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify Japanese text is present
    assert "サンプル台詞" in content
    # Verify English text is not present
    assert "Example dialogue line" not in content
    # Verify no fallback warning is emitted for supported language
    warning_found = any("not supported" in step for step in result.next_steps)
    assert not warning_found, (
        f"Unexpected fallback warning for supported language: {result.next_steps}"
    )


def test_seed_data_matches_source_language_chinese(tmp_path: Path) -> None:
    """Test that seed data is generated in Chinese when source_language is zh."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="zh",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify Chinese text is present
    assert "示例对话" in content
    # Verify English text is not present
    assert "Example dialogue line" not in content


def test_seed_data_matches_source_language_korean(tmp_path: Path) -> None:
    """Test that seed data is generated in Korean when source_language is ko."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ko",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify Korean text is present
    assert "샘플 대사" in content
    # Verify English text is not present
    assert "Example dialogue line" not in content


def test_seed_data_matches_source_language_spanish(tmp_path: Path) -> None:
    """Test that seed data is generated in Spanish when source_language is es."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="es",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify Spanish text is present
    assert "Línea de diálogo de ejemplo" in content
    # Verify English text is not present
    assert "Example dialogue line 1" not in content


def test_seed_data_matches_source_language_french(tmp_path: Path) -> None:
    """Test that seed data is generated in French when source_language is fr."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="fr",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify French text is present
    assert "Ligne de dialogue exemple" in content
    # Verify English text is not present
    assert "Example dialogue line" not in content


def test_seed_data_matches_source_language_german(tmp_path: Path) -> None:
    """Test that seed data is generated in German when source_language is de."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="de",
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify German text is present
    assert "Beispiel-Dialogzeile" in content
    # Verify English text is not present
    assert "Example dialogue line" not in content


def test_seed_data_matches_source_language_english(tmp_path: Path) -> None:
    """Test that seed data is generated in English when source_language is en."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="en",
        target_languages=["ja"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify English text is present
    assert "Example dialogue line" in content


def test_seed_data_unsupported_language_falls_back_to_english(
    tmp_path: Path,
) -> None:
    """Test that unsupported languages fall back to English with warning."""
    answers = InitAnswers(
        project_name="test_project",
        game_name="test_game",
        source_language="ru",  # Russian - not in supported list
        target_languages=["en"],
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3-30b-a3b",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    result = generate_project(answers, tmp_path)
    seed_path = tmp_path / "input" / f"{answers.game_name}.jsonl"

    content = seed_path.read_text(encoding="utf-8")
    # Verify English fallback text is present
    assert "Example dialogue line" in content

    # Verify warning is present in next_steps
    warning_found = any(
        "language 'ru' not supported" in step and "Replace the content" in step
        for step in result.next_steps
    )
    assert warning_found, (
        f"Expected fallback warning in next_steps, got: {result.next_steps}"
    )
