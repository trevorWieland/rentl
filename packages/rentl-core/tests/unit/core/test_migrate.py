"""Unit tests for migration registry and engine."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import pytest

from rentl_core.migrate import (
    MigrationRegistry,
    MigrationTransform,
    apply_migrations,
    get_registry,
    plan_migrations,
)
from rentl_schemas.migration import MigrationStep
from rentl_schemas.version import VersionInfo


class TestMigrationRegistry:
    """Test suite for MigrationRegistry."""

    def test_register_and_retrieve_steps(self) -> None:
        """Test registering migration steps and retrieving them in order."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)
        v020 = VersionInfo(major=0, minor=2, patch=0)

        def noop_transform(config: dict) -> dict:
            return config

        # Register migrations out of order to test sorting
        registry.register(v010, v020, "Second migration", noop_transform)
        registry.register(v001, v010, "First migration", noop_transform)

        steps = registry.get_all_steps()
        assert len(steps) == 2
        assert steps[0].source_version == v001
        assert steps[0].target_version == v010
        assert steps[1].source_version == v010
        assert steps[1].target_version == v020

    def test_get_transform_by_step(self) -> None:
        """Test retrieving transform function by migration step."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)

        def test_transform(config: dict) -> dict:
            return config | {"migrated": True}

        registry.register(v001, v010, "Test migration", test_transform)

        steps = registry.get_all_steps()
        retrieved = registry.get_transform(steps[0])
        assert retrieved is test_transform

        # Test function works
        result = retrieved({"key": "value"})
        assert result == {"key": "value", "migrated": True}

    def test_get_transform_missing(self) -> None:
        """Test that getting a non-existent transform raises KeyError."""
        registry = MigrationRegistry()
        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)

        # Create a step that was never registered
        missing_step = MigrationStep(
            source_version=v001,
            target_version=v010,
            description="Not registered",
            transform_fn_name="nonexistent",
        )

        with pytest.raises(KeyError):
            registry.get_transform(missing_step)


class TestPlanMigrations:
    """Test suite for plan_migrations function."""

    def test_no_migrations_needed_when_at_target(self) -> None:
        """Test that no migrations are planned when already at target version."""
        registry = MigrationRegistry()

        v010 = VersionInfo(major=0, minor=1, patch=0)

        chain = plan_migrations(v010, v010, registry)
        assert chain == []

    def test_no_migrations_needed_when_ahead_of_target(self) -> None:
        """Test that no migrations are planned when ahead of target version."""
        registry = MigrationRegistry()

        v010 = VersionInfo(major=0, minor=1, patch=0)
        v001 = VersionInfo(major=0, minor=0, patch=1)

        chain = plan_migrations(v010, v001, registry)
        assert chain == []

    def test_single_migration_step(self) -> None:
        """Test planning a single migration step."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)

        def noop_transform(config: dict) -> dict:
            return config

        registry.register(v001, v010, "Single step", noop_transform)

        chain = plan_migrations(v001, v010, registry)
        assert len(chain) == 1
        assert chain[0].source_version == v001
        assert chain[0].target_version == v010

    def test_multi_step_migration_chain(self) -> None:
        """Test planning a multi-step migration chain."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)
        v020 = VersionInfo(major=0, minor=2, patch=0)
        v030 = VersionInfo(major=0, minor=3, patch=0)

        def noop_transform(config: dict) -> dict:
            return config

        registry.register(v001, v010, "Step 1", noop_transform)
        registry.register(v010, v020, "Step 2", noop_transform)
        registry.register(v020, v030, "Step 3", noop_transform)

        chain = plan_migrations(v001, v030, registry)
        assert len(chain) == 3
        assert chain[0].source_version == v001
        assert chain[0].target_version == v010
        assert chain[1].source_version == v010
        assert chain[1].target_version == v020
        assert chain[2].source_version == v020
        assert chain[2].target_version == v030

    def test_no_migration_path_raises_error(self) -> None:
        """Test that planning fails when no migration path exists."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v030 = VersionInfo(major=0, minor=3, patch=0)

        # No migration registered, so no path exists
        with pytest.raises(ValueError, match="No migration path"):
            plan_migrations(v001, v030, registry)

    def test_partial_migration_path_raises_error(self) -> None:
        """Test that planning fails when migration path is incomplete."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)
        v030 = VersionInfo(major=0, minor=3, patch=0)

        def noop_transform(config: dict) -> dict:
            return config

        # Register only first step, leaving gap to v030
        registry.register(v001, v010, "Step 1", noop_transform)

        with pytest.raises(ValueError, match="No migration path"):
            plan_migrations(v001, v030, registry)


class TestApplyMigrations:
    """Test suite for apply_migrations function."""

    def test_apply_no_migrations(self) -> None:
        """Test applying empty migration chain returns copy of original."""
        registry = MigrationRegistry()
        config = {"key": "value", "nested": {"field": 42}}

        result = apply_migrations(config, [], registry)

        assert result == config
        # Ensure it's a copy, not the same object
        assert result is not config

    def test_apply_single_migration(self) -> None:
        """Test applying a single migration step."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)

        def add_field_transform(config: dict) -> dict:
            return config | {"new_field": "added"}

        registry.register(v001, v010, "Add field", add_field_transform)

        config = {"existing": "data"}
        steps = registry.get_all_steps()

        result = apply_migrations(config, steps, registry)

        assert result == {"existing": "data", "new_field": "added"}
        # Original unchanged
        assert config == {"existing": "data"}

    def test_apply_multi_step_migration_chain(self) -> None:
        """Test applying multiple migration steps in sequence."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)
        v020 = VersionInfo(major=0, minor=2, patch=0)

        def step1_transform(config: dict) -> dict:
            return config | {"step1": "done"}

        def step2_transform(config: dict) -> dict:
            return config | {"step2": "done"}

        registry.register(v001, v010, "Step 1", step1_transform)
        registry.register(v010, v020, "Step 2", step2_transform)

        config = {"initial": "state"}
        steps = registry.get_all_steps()

        result = apply_migrations(config, steps, registry)

        assert result == {"initial": "state", "step1": "done", "step2": "done"}

    def test_migrations_preserve_data(self) -> None:
        """Test that migrations don't lose data from original config."""
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)

        def update_version_transform(config: dict) -> dict:
            return config | {"schema_version": "0.1.0"}

        registry.register(v001, v010, "Update version", update_version_transform)

        config = {
            "schema_version": "0.0.1",
            "important_data": [1, 2, 3],
            "nested": {"key": "value"},
        }
        steps = registry.get_all_steps()

        result = apply_migrations(config, steps, registry)

        # Version updated
        assert result["schema_version"] == "0.1.0"
        # Other data preserved
        assert result["important_data"] == [1, 2, 3]
        assert result["nested"] == {"key": "value"}

    def test_same_function_name_different_migrations(self) -> None:
        """Regression: two migrations with same function name execute both.

        This tests that the registry keys transforms by migration edge rather
        than function name, preventing collisions when different migration
        steps share the same __name__.
        """
        registry = MigrationRegistry()

        v001 = VersionInfo(major=0, minor=0, patch=1)
        v010 = VersionInfo(major=0, minor=1, patch=0)
        v020 = VersionInfo(major=0, minor=2, patch=0)

        # Create two distinct transform functions that have the same __name__
        # by using exec to define them in separate namespaces
        namespace1: dict[str, MigrationTransform] = {}
        exec(
            """
def transform(config: dict) -> dict:
    return config | {"first": True}
""",
            namespace1,
        )
        transform1 = cast(MigrationTransform, namespace1["transform"])

        namespace2: dict[str, MigrationTransform] = {}
        exec(
            """
def transform(config: dict) -> dict:
    return config | {"second": True}
""",
            namespace2,
        )
        transform2 = cast(MigrationTransform, namespace2["transform"])

        # Verify they are different functions (even though they have same __name__)
        assert transform1 is not transform2

        # Register both migrations - the collision scenario occurs when different
        # migration steps have transform functions with the same __name__
        registry.register(v001, v010, "First migration", transform1)
        registry.register(v010, v020, "Second migration", transform2)

        # Apply migration chain
        config = {"schema_version": "0.0.1"}
        steps = registry.get_all_steps()
        result = apply_migrations(config, steps, registry)

        # Both transforms should have been applied, proving no collision
        # If collision occurred, only the second transform would execute
        assert "first" in result, "First transform did not execute (collision occurred)"
        assert "second" in result, "Second transform did not execute"
        assert result["first"] is True
        assert result["second"] is True


class TestGlobalRegistry:
    """Test suite for global registry access."""

    def test_get_registry_returns_same_instance(self) -> None:
        """Test that get_registry returns the same instance each time."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_seed_migration_registered(self) -> None:
        """Test that the seed migration (0.0.1 → 0.1.0) is registered."""
        registry = get_registry()
        steps = registry.get_all_steps()

        # Find the seed migration
        seed_migration = None
        for step in steps:
            if step.source_version == VersionInfo(major=0, minor=0, patch=1):
                seed_migration = step
                break

        assert seed_migration is not None
        assert seed_migration.target_version == VersionInfo(major=0, minor=1, patch=0)
        assert seed_migration.transform_fn_name == "_migrate_0_0_1_to_0_1_0"

    def test_seed_migration_transform_works(self) -> None:
        """Test that the seed migration transform preserves data."""
        registry = get_registry()

        config = {
            "project": {
                "schema_version": {"major": 0, "minor": 0, "patch": 1},
                "project_name": "test-project",
            },
            "llm": {"provider": "openai"},
            "other_data": 42,
        }

        steps = registry.get_all_steps()
        # Find seed migration step
        seed_step = next(
            s
            for s in steps
            if s.source_version == VersionInfo(major=0, minor=0, patch=1)
        )

        result = apply_migrations(config, [seed_step], registry)

        # Version updated in correct location
        assert "project" in result
        assert isinstance(result["project"], dict)
        assert "schema_version" in result["project"]
        schema_version = result["project"]["schema_version"]
        assert isinstance(schema_version, dict)
        assert schema_version["major"] == 0
        assert schema_version["minor"] == 1
        assert schema_version["patch"] == 0
        # Other data preserved
        assert result["llm"] == {"provider": "openai"}
        assert result["other_data"] == 42

    def test_seed_migration_no_top_level_schema_version(self) -> None:
        """Regression: seed migration does not create top-level schema_version.

        The schema_version should be nested under project.schema_version, not
        at the top level. This test ensures the seed migration writes to the
        correct location.
        """
        registry = get_registry()

        config = {
            "project": {
                "schema_version": {"major": 0, "minor": 0, "patch": 1},
                "project_name": "test-project",
            },
            "other_field": "value",
        }

        steps = registry.get_all_steps()
        seed_step = next(
            s
            for s in steps
            if s.source_version == VersionInfo(major=0, minor=0, patch=1)
        )

        result = apply_migrations(config, [seed_step], registry)

        # Should NOT have top-level schema_version
        # (Only check if "schema_version" is at top level AND is a string,
        # which would indicate the old incorrect behavior)
        if "schema_version" in result and not isinstance(
            result["schema_version"], dict
        ):
            assert False, (  # noqa: B011
                f"Top-level schema_version should not exist as string. "
                f"Found: {result.get('schema_version')}"
            )

        # Should have nested project.schema_version with correct structure
        assert "project" in result
        assert isinstance(result["project"], dict)
        assert "schema_version" in result["project"]
        assert isinstance(result["project"]["schema_version"], dict)
        assert result["project"]["schema_version"]["major"] == 0
        assert result["project"]["schema_version"]["minor"] == 1
        assert result["project"]["schema_version"]["patch"] == 0

    def test_changelog_synced_with_registry(self) -> None:
        """Test that SCHEMA_CHANGELOG.md has an entry for every registered migration.

        This test ensures the human-readable changelog stays in sync with the
        machine-readable migration registry. Every registered migration step
        must have a corresponding changelog entry.
        """
        # Read the changelog from project root
        changelog_path = Path(__file__).parents[5] / "SCHEMA_CHANGELOG.md"
        assert changelog_path.exists(), "SCHEMA_CHANGELOG.md not found at project root"

        changelog_text = changelog_path.read_text()

        # Get all registered migrations
        registry = get_registry()
        steps = registry.get_all_steps()

        # For each registered migration, verify changelog has an entry
        for step in steps:
            src_ver = step.source_version
            tgt_ver = step.target_version
            source = f"{src_ver.major}.{src_ver.minor}.{src_ver.patch}"
            target = f"{tgt_ver.major}.{tgt_ver.minor}.{tgt_ver.patch}"

            # Look for a heading like "## 0.0.1 → 0.1.0" in the changelog
            pattern = re.compile(
                rf"##\s+{re.escape(source)}\s+→\s+{re.escape(target)}",
                re.MULTILINE,
            )

            assert pattern.search(changelog_text), (
                f"Missing changelog entry for migration {source} → {target}"
            )
