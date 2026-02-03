"""Shared fixtures for quality agent evals."""

from __future__ import annotations

import pytest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.settings import ModelSettings

from tests.quality.agents.quality_harness import (
    QualityModelConfig,
    build_judge_model,
    build_judge_settings,
    load_quality_model_config,
)


@pytest.fixture(scope="session")
def quality_model_config() -> QualityModelConfig:
    """Load quality model configuration once per test session.

    Returns:
        Quality model configuration.
    """
    return load_quality_model_config()


@pytest.fixture(scope="session")
def quality_judge_model(
    quality_model_config: QualityModelConfig,
) -> OpenAIChatModel:
    """Build the LLM judge model once per test session.

    Returns:
        Configured judge model.
    """
    return build_judge_model(quality_model_config)


@pytest.fixture(scope="session")
def quality_judge_settings() -> ModelSettings:
    """Provide judge model settings.

    Returns:
        Judge model settings.
    """
    return build_judge_settings()
