"""Compatibility verification schemas for multi-model testing."""

from __future__ import annotations

import importlib.resources
import tomllib
from typing import Literal

from pydantic import Field, field_validator, model_validator

from rentl_schemas.base import BaseSchema

EndpointType = Literal["local", "openrouter"]


class VerifiedModelConfigOverrides(BaseSchema):
    """Per-model configuration overrides for verification runs."""

    timeout_s: float | None = Field(
        None, gt=0, description="Request timeout override in seconds"
    )
    temperature: float | None = Field(
        None, ge=0, le=2, description="Sampling temperature override"
    )
    max_output_tokens: int | None = Field(
        None, ge=1, description="Maximum output tokens override"
    )
    reasoning_effort: str | None = Field(
        None, description="Reasoning effort level override"
    )
    top_p: float | None = Field(None, ge=0, le=1, description="Top-p sampling override")


class VerifiedModelEntry(BaseSchema):
    """A single model entry in the verified-models registry."""

    model_id: str = Field(
        ..., min_length=1, description="Provider-specific model identifier"
    )
    endpoint_type: EndpointType = Field(
        ..., description="Endpoint type: local (LM Studio) or openrouter"
    )
    endpoint_ref: str = Field(
        ..., min_length=1, description="Reference to configured endpoint name"
    )
    load_endpoint: str | None = Field(
        None,
        min_length=1,
        description="LM Studio model load API URL for local models",
    )
    config_overrides: VerifiedModelConfigOverrides = Field(
        default_factory=VerifiedModelConfigOverrides,
        description="Per-model configuration overrides",
    )

    @field_validator("endpoint_type", mode="before")
    @classmethod
    def _coerce_endpoint_type(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError(
                f"endpoint_type must be a string, got {type(value).__name__}"
            )
        return value.lower()

    @model_validator(mode="after")
    def validate_local_requires_load_endpoint(self) -> VerifiedModelEntry:
        """Ensure local models specify a load_endpoint.

        Returns:
            VerifiedModelEntry: Validated entry.

        Raises:
            ValueError: If a local model is missing load_endpoint.
        """
        if self.endpoint_type == "local" and not self.load_endpoint:
            raise ValueError(
                "local models must specify load_endpoint for LM Studio model loading"
            )
        if self.endpoint_type == "openrouter" and self.load_endpoint:
            raise ValueError("openrouter models must not specify load_endpoint")
        return self


class VerifiedModelRegistry(BaseSchema):
    """Complete verified-models registry loaded from TOML."""

    models: list[VerifiedModelEntry] = Field(
        ..., min_length=1, description="List of verified model entries"
    )

    @model_validator(mode="after")
    def validate_unique_model_ids(self) -> VerifiedModelRegistry:
        """Ensure model IDs are unique across the registry.

        Returns:
            VerifiedModelRegistry: Validated registry.

        Raises:
            ValueError: If model IDs are duplicated.
        """
        ids = [m.model_id for m in self.models]
        if len(set(ids)) != len(ids):
            dupes = sorted({mid for mid in ids if ids.count(mid) > 1})
            raise ValueError(f"duplicate model_id values: {', '.join(dupes)}")
        return self

    def filter_by_endpoint(
        self, endpoint_type: EndpointType
    ) -> list[VerifiedModelEntry]:
        """Return models matching the given endpoint type.

        Args:
            endpoint_type: Filter to local or openrouter models.

        Returns:
            list[VerifiedModelEntry]: Matching model entries.
        """
        return [m for m in self.models if m.endpoint_type == endpoint_type]

    def get_model(self, model_id: str) -> VerifiedModelEntry | None:
        """Look up a model by ID.

        Args:
            model_id: The model identifier to find.

        Returns:
            VerifiedModelEntry | None: The matching entry, or None.
        """
        for m in self.models:
            if m.model_id == model_id:
                return m
        return None


def load_registry_from_toml(toml_text: str) -> VerifiedModelRegistry:
    """Parse TOML text into a validated VerifiedModelRegistry.

    Args:
        toml_text: Raw TOML content with a [[models]] array.

    Returns:
        VerifiedModelRegistry: Validated registry.
    """
    data = tomllib.loads(toml_text)
    # TOML [[models]] becomes a list of dicts under "models" key
    raw_models = data.get("models", [])
    # Nest config_overrides from flat TOML [models.config_overrides] tables
    return VerifiedModelRegistry(models=raw_models)


def load_bundled_registry() -> VerifiedModelRegistry:
    """Load the bundled verified-models registry shipped with rentl-schemas.

    Returns:
        VerifiedModelRegistry: Validated registry from the package data.
    """
    data_pkg = importlib.resources.files("rentl_schemas") / "data"
    registry_path = data_pkg / "verified_models.toml"
    toml_text = registry_path.read_text(encoding="utf-8")
    return load_registry_from_toml(toml_text)
