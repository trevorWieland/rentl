"""Unit tests for benchmark configuration schemas."""

import pytest
from pydantic import ValidationError

from rentl_schemas.benchmark.config import (
    BenchmarkConfig,
    EvalSetConfig,
    SliceConfig,
)


def test_slice_config_valid() -> None:
    """Test SliceConfig with valid data."""
    slice_config = SliceConfig(
        name="demo",
        description="Demo slice for testing",
        scene_ids=["scene1", "scene2"],
        line_range=(1, 10),
        max_lines=20,
    )
    assert slice_config.name == "demo"
    assert slice_config.scene_ids == ["scene1", "scene2"]
    assert slice_config.line_range == (1, 10)
    assert slice_config.max_lines == 20


def test_slice_config_minimal() -> None:
    """Test SliceConfig with minimal required fields."""
    slice_config = SliceConfig(
        name="minimal",
        description="Minimal slice",
        scene_ids=["scene1"],
    )
    assert slice_config.name == "minimal"
    assert slice_config.line_range is None
    assert slice_config.max_lines is None


def test_slice_config_roundtrip() -> None:
    """Test SliceConfig serialization roundtrip."""
    original = SliceConfig(
        name="test",
        description="Test slice",
        scene_ids=["s1", "s2", "s3"],
        max_lines=50,
    )
    json_data = original.model_dump()
    reconstructed = SliceConfig.model_validate(json_data)
    assert reconstructed == original


def test_eval_set_config_valid() -> None:
    """Test EvalSetConfig with valid data."""
    eval_set = EvalSetConfig(
        name="katawa-shoujo",
        source_language="ja",
        target_language="en",
        download_url="https://github.com/example/ksre/archive/main.zip",
        hash_manifest_path="benchmarks/katawa-shoujo/hashes.json",
        has_reference=True,
        slices=[
            SliceConfig(
                name="demo",
                description="Demo slice",
                scene_ids=["a1_monday"],
            )
        ],
    )
    assert eval_set.name == "katawa-shoujo"
    assert eval_set.source_language == "ja"
    assert eval_set.target_language == "en"
    assert eval_set.has_reference is True
    assert len(eval_set.slices) == 1


def test_eval_set_config_no_slices() -> None:
    """Test EvalSetConfig with no slices defaults to empty list."""
    eval_set = EvalSetConfig(
        name="test-set",
        source_language="ja",
        target_language="en",
        download_url="https://example.com/data.zip",
        hash_manifest_path="hashes.json",
        has_reference=False,
    )
    assert eval_set.slices == []


def test_eval_set_config_roundtrip() -> None:
    """Test EvalSetConfig serialization roundtrip."""
    original = EvalSetConfig(
        name="test",
        source_language="ja",
        target_language="en",
        download_url="https://example.com/data.zip",
        hash_manifest_path="hashes.json",
        has_reference=True,
    )
    json_data = original.model_dump()
    reconstructed = EvalSetConfig.model_validate(json_data)
    assert reconstructed == original


def test_benchmark_config_valid() -> None:
    """Test BenchmarkConfig with valid data."""
    config = BenchmarkConfig(
        eval_set="katawa-shoujo",
        slice_name="demo",
        scoring_mode="reference_based",
        judge_model="gpt-4o",
        judge_base_url="https://api.openai.com/v1",
        head_to_head=True,
        output_path="/tmp/benchmark.json",
    )
    assert config.eval_set == "katawa-shoujo"
    assert config.slice_name == "demo"
    assert config.scoring_mode == "reference_based"
    assert config.judge_model == "gpt-4o"
    assert config.head_to_head is True


def test_benchmark_config_minimal() -> None:
    """Test BenchmarkConfig with minimal required fields."""
    config = BenchmarkConfig(
        eval_set="test-set",
        judge_model="gpt-4o",
    )
    assert config.slice_name is None
    assert config.scoring_mode == "reference_based"
    assert config.judge_base_url is None
    assert config.head_to_head is False
    assert config.output_path is None


def test_benchmark_config_scoring_mode_validation() -> None:
    """Test BenchmarkConfig scoring_mode validates against literal values."""
    # Valid scoring modes
    for mode in ["reference_based", "reference_free"]:
        config = BenchmarkConfig(
            eval_set="test",
            scoring_mode=mode,  # type: ignore[arg-type]
            judge_model="gpt-4o",
        )
        assert config.scoring_mode == mode

    # Invalid scoring mode
    with pytest.raises(ValidationError):
        BenchmarkConfig(
            eval_set="test",
            scoring_mode="invalid",  # type: ignore[arg-type]
            judge_model="gpt-4o",
        )


def test_benchmark_config_roundtrip() -> None:
    """Test BenchmarkConfig serialization roundtrip."""
    original = BenchmarkConfig(
        eval_set="test",
        slice_name="demo",
        scoring_mode="reference_free",
        judge_model="claude-3-5-sonnet-20241022",
        head_to_head=True,
    )
    json_data = original.model_dump()
    reconstructed = BenchmarkConfig.model_validate(json_data)
    assert reconstructed == original
