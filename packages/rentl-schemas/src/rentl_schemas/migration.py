"""Migration step schema for config schema versioning."""

from __future__ import annotations

from typing import ClassVar

from pydantic import ConfigDict, Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.version import VersionInfo


class MigrationStep(BaseSchema):
    """A single migration step from one schema version to another.

    Each migration step is a pure function that transforms a config dict
    from source_version to target_version. The transform function takes a
    dict and returns a dict, with no side effects.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    source_version: VersionInfo = Field(
        ..., description="Version this migration starts from"
    )
    target_version: VersionInfo = Field(
        ..., description="Version this migration produces"
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of what this migration changes",
    )
    transform_fn_name: str = Field(
        ...,
        min_length=1,
        description=(
            "Name of the pure function that transforms config dict "
            "from source to target version"
        ),
    )

    def __str__(self) -> str:
        """Return readable migration step description."""
        return f"{self.source_version} → {self.target_version}: {self.description}"
