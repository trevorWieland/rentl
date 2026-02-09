"""Unit tests for MigrationStep schema."""

import pytest
from pydantic import ValidationError

from rentl_schemas.migration import MigrationStep
from rentl_schemas.version import VersionInfo


def test_migration_step_creation() -> None:
    """Ensure MigrationStep can be created with valid data."""
    source = VersionInfo(major=0, minor=0, patch=1)
    target = VersionInfo(major=0, minor=1, patch=0)

    step = MigrationStep(
        source_version=source,
        target_version=target,
        description="Initial migration to v0.1.0 schema",
    )

    assert step.source_version == source
    assert step.target_version == target
    assert step.description == "Initial migration to v0.1.0 schema"


def test_migration_step_string_representation() -> None:
    """Ensure MigrationStep has readable string representation."""
    source = VersionInfo(major=0, minor=0, patch=1)
    target = VersionInfo(major=0, minor=1, patch=0)

    step = MigrationStep(
        source_version=source,
        target_version=target,
        description="Test migration",
    )

    expected = "0.0.1 → 0.1.0: Test migration"
    assert str(step) == expected


def test_migration_step_requires_description() -> None:
    """Ensure MigrationStep requires a non-empty description."""
    source = VersionInfo(major=0, minor=0, patch=1)
    target = VersionInfo(major=0, minor=1, patch=0)

    # Empty description should fail validation
    with pytest.raises(ValidationError) as exc_info:
        MigrationStep(
            source_version=source,
            target_version=target,
            description="",
        )

    errors = exc_info.value.errors()
    assert any("description" in str(e["loc"]) for e in errors)


def test_migration_step_requires_all_fields() -> None:
    """Ensure MigrationStep requires all mandatory fields."""
    # Missing source_version
    with pytest.raises(ValidationError) as exc_info:
        MigrationStep(  # type: ignore[call-arg]
            target_version=VersionInfo(major=0, minor=1, patch=0),
            description="Test",
        )
    errors = exc_info.value.errors()
    assert any("source_version" in str(e["loc"]) for e in errors)

    # Missing target_version
    with pytest.raises(ValidationError) as exc_info:
        MigrationStep(  # type: ignore[call-arg]
            source_version=VersionInfo(major=0, minor=0, patch=1),
            description="Test",
        )
    errors = exc_info.value.errors()
    assert any("target_version" in str(e["loc"]) for e in errors)

    # Missing description
    with pytest.raises(ValidationError) as exc_info:
        MigrationStep(  # type: ignore[call-arg]
            source_version=VersionInfo(major=0, minor=0, patch=1),
            target_version=VersionInfo(major=0, minor=1, patch=0),
        )
    errors = exc_info.value.errors()
    assert any("description" in str(e["loc"]) for e in errors)


def test_migration_step_validation() -> None:
    """Test that MigrationStep validates version info properly."""
    # Valid migration step
    step = MigrationStep(
        source_version=VersionInfo(major=1, minor=0, patch=0),
        target_version=VersionInfo(major=1, minor=1, patch=0),
        description="Add new field",
    )

    assert step.source_version.major == 1
    assert step.target_version.minor == 1


def test_migration_step_serialization() -> None:
    """Test that MigrationStep can be serialized and deserialized."""
    step = MigrationStep(
        source_version=VersionInfo(major=0, minor=0, patch=1),
        target_version=VersionInfo(major=0, minor=1, patch=0),
        description="Test migration",
    )

    # Serialize to dict
    step_dict = step.model_dump()
    assert step_dict["source_version"]["major"] == 0
    assert step_dict["source_version"]["minor"] == 0
    assert step_dict["source_version"]["patch"] == 1
    assert step_dict["target_version"]["major"] == 0
    assert step_dict["target_version"]["minor"] == 1
    assert step_dict["target_version"]["patch"] == 0
    assert step_dict["description"] == "Test migration"

    # Deserialize from dict
    reconstructed = MigrationStep.model_validate(step_dict)
    assert reconstructed.source_version == step.source_version
    assert reconstructed.target_version == step.target_version
    assert reconstructed.description == step.description
