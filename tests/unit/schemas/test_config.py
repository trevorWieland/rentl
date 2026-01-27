"""Unit tests for configuration schema validation."""

import pytest
from pydantic import ValidationError

from rentl_schemas.config import (
    LanguageConfig,
    ModelSettings,
    PhaseConfig,
    PhaseExecutionConfig,
    PipelineConfig,
)
from rentl_schemas.primitives import PhaseName, PhaseWorkStrategy


def test_language_config_rejects_duplicate_targets() -> None:
    """Ensure duplicate target languages are rejected."""
    with pytest.raises(ValidationError):
        LanguageConfig(
            source_language="en",
            target_languages=["ja", "ja"],
        )


def test_language_config_rejects_source_in_targets() -> None:
    """Ensure source language cannot appear in target list."""
    with pytest.raises(ValidationError):
        LanguageConfig(
            source_language="en",
            target_languages=["en", "ja"],
        )


def test_pipeline_config_enforces_phase_order() -> None:
    """Ensure phases follow canonical order."""
    with pytest.raises(ValidationError):
        PipelineConfig(
            default_model=ModelSettings(model_id="gpt-4"),
            phases=[
                PhaseConfig(phase=PhaseName.TRANSLATE),
                PhaseConfig(phase=PhaseName.CONTEXT),
                PhaseConfig(phase=PhaseName.PRETRANSLATION),
                PhaseConfig(phase=PhaseName.QA),
                PhaseConfig(phase=PhaseName.EDIT),
            ],
        )


def test_pipeline_config_requires_default_model() -> None:
    """Ensure default_model is required when phases omit model settings."""
    with pytest.raises(ValidationError):
        PipelineConfig(
            default_model=None,
            phases=[
                PhaseConfig(phase=PhaseName.CONTEXT),
                PhaseConfig(phase=PhaseName.PRETRANSLATION),
                PhaseConfig(phase=PhaseName.TRANSLATE),
                PhaseConfig(phase=PhaseName.QA),
                PhaseConfig(phase=PhaseName.EDIT),
            ],
        )


def test_phase_execution_requires_chunk_size() -> None:
    """Ensure chunk strategy requires chunk_size."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(strategy=PhaseWorkStrategy.CHUNK)


def test_phase_execution_rejects_full_with_chunk_size() -> None:
    """Ensure chunk_size is rejected for full strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.FULL,
            chunk_size=10,
        )


def test_phase_execution_rejects_scene_with_chunk_size() -> None:
    """Ensure chunk_size is rejected for scene strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.SCENE,
            chunk_size=10,
        )


def test_phase_execution_rejects_chunk_with_scene_batch_size() -> None:
    """Ensure scene_batch_size is rejected for chunk strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.CHUNK,
            chunk_size=10,
            scene_batch_size=2,
        )
