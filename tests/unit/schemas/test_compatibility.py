"""Unit tests for compatibility schema validation and TOML loading."""

import pytest
from pydantic import ValidationError

from rentl_schemas.compatibility import (
    VerifiedModelConfigOverrides,
    VerifiedModelEntry,
    VerifiedModelRegistry,
    load_bundled_registry,
    load_registry_from_toml,
)

# ── VerifiedModelEntry ──────────────────────────────────────────


def test_valid_local_entry() -> None:
    """Local model entry with load_endpoint passes validation."""
    entry = VerifiedModelEntry(
        model_id="google/gemma-3-27b",
        endpoint_type="local",
        endpoint_ref="lm-studio",
        load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
    )
    assert entry.endpoint_type == "local"
    assert entry.load_endpoint is not None


def test_valid_openrouter_entry() -> None:
    """OpenRouter model entry without load_endpoint passes validation."""
    entry = VerifiedModelEntry(
        model_id="deepseek/deepseek-v3.2",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
    )
    assert entry.endpoint_type == "openrouter"
    assert entry.load_endpoint is None


def test_local_entry_requires_load_endpoint() -> None:
    """Local model without load_endpoint is rejected."""
    with pytest.raises(ValidationError, match="load_endpoint"):
        VerifiedModelEntry(
            model_id="google/gemma-3-27b",
            endpoint_type="local",
            endpoint_ref="lm-studio",
        )


def test_openrouter_entry_rejects_load_endpoint() -> None:
    """OpenRouter model with load_endpoint is rejected."""
    with pytest.raises(ValidationError, match="load_endpoint"):
        VerifiedModelEntry(
            model_id="deepseek/deepseek-v3.2",
            endpoint_type="openrouter",
            endpoint_ref="openrouter",
            load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
        )


def test_entry_rejects_empty_model_id() -> None:
    """Empty model_id is rejected."""
    with pytest.raises(ValidationError):
        VerifiedModelEntry(
            model_id="",
            endpoint_type="openrouter",
            endpoint_ref="openrouter",
        )


def test_entry_rejects_invalid_endpoint_type() -> None:
    """Invalid endpoint_type is rejected."""
    with pytest.raises(ValidationError):
        VerifiedModelEntry.model_validate({
            "model_id": "some/model",
            "endpoint_type": "azure",
            "endpoint_ref": "azure-endpoint",
        })


def test_entry_rejects_null_endpoint_type() -> None:
    """None endpoint_type raises ValidationError, not AttributeError."""
    with pytest.raises(ValidationError, match="endpoint_type"):
        VerifiedModelEntry.model_validate({
            "model_id": "some/model",
            "endpoint_type": None,
            "endpoint_ref": "some-ref",
        })


def test_entry_rejects_non_string_endpoint_type() -> None:
    """Non-string endpoint_type (e.g., int) raises ValidationError."""
    with pytest.raises(ValidationError, match="endpoint_type"):
        VerifiedModelEntry.model_validate({
            "model_id": "some/model",
            "endpoint_type": 42,
            "endpoint_ref": "some-ref",
        })


def test_config_overrides_defaults() -> None:
    """Config overrides default to None for all fields."""
    overrides = VerifiedModelConfigOverrides()
    assert overrides.timeout_s is None
    assert overrides.temperature is None
    assert overrides.max_output_tokens is None
    assert overrides.max_output_retries is None
    assert overrides.supports_tool_choice_required is None
    assert overrides.load_timeout_s is None


def test_config_overrides_validates_bounds() -> None:
    """Config override values respect constraints."""
    overrides = VerifiedModelConfigOverrides(
        timeout_s=120.0,
        temperature=0.5,
        max_output_tokens=8192,
    )
    assert overrides.timeout_s == pytest.approx(120.0)
    assert overrides.temperature == pytest.approx(0.5)
    assert overrides.max_output_tokens == 8192


def test_config_overrides_max_output_retries_validation() -> None:
    """max_output_retries accepts valid values and rejects negative."""
    overrides = VerifiedModelConfigOverrides(max_output_retries=4)
    assert overrides.max_output_retries == 4
    overrides_zero = VerifiedModelConfigOverrides(max_output_retries=0)
    assert overrides_zero.max_output_retries == 0
    with pytest.raises(ValidationError):
        VerifiedModelConfigOverrides(max_output_retries=-1)


def test_config_overrides_supports_tool_choice_required_validation() -> None:
    """supports_tool_choice_required accepts bool values."""
    overrides_true = VerifiedModelConfigOverrides(supports_tool_choice_required=True)
    assert overrides_true.supports_tool_choice_required is True
    overrides_false = VerifiedModelConfigOverrides(supports_tool_choice_required=False)
    assert overrides_false.supports_tool_choice_required is False


def test_config_overrides_load_timeout_s_validation() -> None:
    """load_timeout_s accepts positive values and rejects non-positive."""
    overrides = VerifiedModelConfigOverrides(load_timeout_s=120.0)
    assert overrides.load_timeout_s == pytest.approx(120.0)
    with pytest.raises(ValidationError):
        VerifiedModelConfigOverrides(load_timeout_s=-1.0)
    with pytest.raises(ValidationError):
        VerifiedModelConfigOverrides(load_timeout_s=0.0)


def test_config_overrides_rejects_negative_timeout() -> None:
    """Negative timeout is rejected."""
    with pytest.raises(ValidationError):
        VerifiedModelConfigOverrides(timeout_s=-1.0)


# ── VerifiedModelRegistry ──────────────────────────────────────


def test_registry_rejects_empty_models() -> None:
    """Registry with no models is rejected."""
    with pytest.raises(ValidationError):
        VerifiedModelRegistry(models=[])


def test_registry_rejects_duplicate_model_ids() -> None:
    """Registry with duplicate model_id values is rejected."""
    entry = VerifiedModelEntry(
        model_id="deepseek/deepseek-v3.2",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
    )
    with pytest.raises(ValidationError, match="duplicate"):
        VerifiedModelRegistry(models=[entry, entry])


def test_registry_filter_by_endpoint() -> None:
    """filter_by_endpoint returns only matching entries."""
    local = VerifiedModelEntry(
        model_id="google/gemma-3-27b",
        endpoint_type="local",
        endpoint_ref="lm-studio",
        load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
    )
    cloud = VerifiedModelEntry(
        model_id="deepseek/deepseek-v3.2",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
    )
    registry = VerifiedModelRegistry(models=[local, cloud])
    assert len(registry.filter_by_endpoint("local")) == 1
    assert len(registry.filter_by_endpoint("openrouter")) == 1


def test_registry_get_model_found() -> None:
    """get_model returns the matching entry."""
    entry = VerifiedModelEntry(
        model_id="deepseek/deepseek-v3.2",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
    )
    registry = VerifiedModelRegistry(models=[entry])
    assert registry.get_model("deepseek/deepseek-v3.2") is not None


def test_registry_get_model_not_found() -> None:
    """get_model returns None for missing model."""
    entry = VerifiedModelEntry(
        model_id="deepseek/deepseek-v3.2",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
    )
    registry = VerifiedModelRegistry(models=[entry])
    assert registry.get_model("nonexistent/model") is None


# ── TOML loading ───────────────────────────────────────────────


MINIMAL_TOML = """\
[[models]]
model_id = "test/model-a"
endpoint_type = "openrouter"
endpoint_ref = "openrouter"

[[models]]
model_id = "test/model-b"
endpoint_type = "local"
endpoint_ref = "lm-studio"
load_endpoint = "http://localhost:1234/api/v1/models/load"

[models.config_overrides]
timeout_s = 300.0
"""


def test_load_registry_from_toml_minimal() -> None:
    """Minimal TOML with two models parses successfully."""
    registry = load_registry_from_toml(MINIMAL_TOML)
    assert len(registry.models) == 2
    assert registry.models[0].model_id == "test/model-a"
    assert registry.models[1].config_overrides.timeout_s == pytest.approx(300.0)


def test_load_registry_from_toml_rejects_empty() -> None:
    """TOML with no models section is rejected."""
    with pytest.raises(ValidationError):
        load_registry_from_toml("")


def test_load_bundled_registry() -> None:
    """Bundled TOML registry loads and validates all 4 models."""
    registry = load_bundled_registry()
    assert len(registry.models) == 4
    local_models = registry.filter_by_endpoint("local")
    openrouter_models = registry.filter_by_endpoint("openrouter")
    assert len(local_models) == 2
    assert len(openrouter_models) == 2


def test_bundled_registry_local_models_have_load_endpoint() -> None:
    """Every local model in the bundled registry has a load_endpoint."""
    registry = load_bundled_registry()
    for model in registry.filter_by_endpoint("local"):
        assert model.load_endpoint is not None


def test_bundled_registry_model_ids_match_spec() -> None:
    """Bundled registry contains exactly the 4 verified models."""
    registry = load_bundled_registry()
    ids = {m.model_id for m in registry.models}
    expected = {
        # Local
        "qwen/qwen3-vl-30b",
        "openai/gpt-oss-20b",
        # OpenRouter
        "openai/gpt-oss-120b",
        "minimax/minimax-m2.5",
    }
    assert ids == expected


def test_bundled_registry_local_models_have_load_timeout_s() -> None:
    """Local models in the bundled registry declare load_timeout_s."""
    registry = load_bundled_registry()
    for model in registry.filter_by_endpoint("local"):
        assert model.config_overrides.load_timeout_s is not None, (
            f"Local model '{model.model_id}' must declare load_timeout_s"
        )


def test_bundled_registry_gpt_oss_120b_max_output_retries() -> None:
    """openai/gpt-oss-120b declares max_output_retries=1 in TOML."""
    registry = load_bundled_registry()
    entry = registry.get_model("openai/gpt-oss-120b")
    assert entry is not None
    assert entry.config_overrides.max_output_retries == 1
