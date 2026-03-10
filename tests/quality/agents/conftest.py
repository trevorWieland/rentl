"""Shared fixtures for quality agent evals."""

from __future__ import annotations

import pytest
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from tests.quality.agents.quality_harness import (
    QualityModelConfig,
    build_judge_model_and_settings,
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
) -> Model:
    """Build the LLM judge model once per test session.

    Returns:
        Configured judge model.
    """
    model, _ = build_judge_model_and_settings(quality_model_config)
    return model


@pytest.fixture(scope="session")
def quality_judge_settings(
    quality_model_config: QualityModelConfig,
) -> ModelSettings:
    """Provide judge model settings from factory.

    Returns:
        Judge model settings.
    """
    _, settings = build_judge_model_and_settings(quality_model_config)
    return settings
