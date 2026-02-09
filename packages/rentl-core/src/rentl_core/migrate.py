"""Config migration registry and engine for schema versioning."""

from __future__ import annotations

from collections.abc import Callable

from rentl_schemas.migration import MigrationStep
from rentl_schemas.version import VersionInfo

# Type alias for config dictionary (unstructured TOML data)
type ConfigDict = dict[str, object]

# Type alias for migration transform functions
type MigrationTransform = Callable[[ConfigDict], ConfigDict]


class MigrationRegistry:
    """Ordered registry of migration steps.

    Maintains a sorted collection of migration steps from oldest to newest.
    Used to plan and apply migrations when upgrading config schemas.
    """

    def __init__(self) -> None:
        """Initialize an empty migration registry."""
        self._steps: list[MigrationStep] = []
        # Key transforms by (source_version, target_version) tuple to avoid
        # name collisions
        self._transforms: dict[tuple[VersionInfo, VersionInfo], MigrationTransform] = {}

    def register(
        self,
        source_version: VersionInfo,
        target_version: VersionInfo,
        description: str,
        transform_fn: MigrationTransform,
    ) -> None:
        """Register a migration step.

        Args:
            source_version: Version this migration starts from
            target_version: Version this migration produces
            description: Human-readable description of changes
            transform_fn: Pure function dict -> dict that applies the migration
        """
        # Get function name, handling both functions and callables
        transform_fn_name = getattr(transform_fn, "__name__", repr(transform_fn))

        step = MigrationStep(
            source_version=source_version,
            target_version=target_version,
            description=description,
            transform_fn_name=transform_fn_name,
        )

        # Insert in sorted order by source_version
        insert_idx = 0
        for i, existing in enumerate(self._steps):
            if existing.source_version > source_version:
                break
            insert_idx = i + 1

        self._steps.insert(insert_idx, step)
        # Key by migration edge to prevent collisions when different migrations
        # have transform functions with the same __name__
        migration_key = (source_version, target_version)
        self._transforms[migration_key] = transform_fn

    def get_all_steps(self) -> list[MigrationStep]:
        """Return all registered migration steps in order.

        Returns:
            List of migration steps, sorted by source version
        """
        return self._steps.copy()

    def get_transform(self, step: MigrationStep) -> MigrationTransform:
        """Get the transform function for a migration step.

        Args:
            step: Migration step to get transform for

        Returns:
            The transform function
        """
        migration_key = (step.source_version, step.target_version)
        return self._transforms[migration_key]


def plan_migrations(
    current_version: VersionInfo,
    target_version: VersionInfo,
    registry: MigrationRegistry,
) -> list[MigrationStep]:
    """Plan the chain of migrations needed to upgrade from current to target version.

    Args:
        current_version: Current schema version
        target_version: Desired schema version
        registry: Migration registry to search

    Returns:
        Ordered list of migration steps to apply, or empty list if already at target

    Raises:
        ValueError: If no migration path exists from current to target version
    """
    if current_version >= target_version:
        return []

    # Build migration chain by following steps from current to target
    chain: list[MigrationStep] = []
    version = current_version
    all_steps = registry.get_all_steps()

    while version < target_version:
        # Find next step that starts from current version
        next_step = None
        for step in all_steps:
            if step.source_version == version and step.target_version <= target_version:
                next_step = step
                break

        if next_step is None:
            raise ValueError(
                f"No migration path from {current_version} to {target_version}. "
                f"Stuck at {version}."
            )

        chain.append(next_step)
        version = next_step.target_version

    return chain


def apply_migrations(
    config_dict: ConfigDict, steps: list[MigrationStep], registry: MigrationRegistry
) -> ConfigDict:
    """Apply a chain of migration steps to a config dict.

    Each migration step is applied in sequence, with the output of one step
    becoming the input to the next. All transforms are pure functions with
    no side effects.

    Args:
        config_dict: Configuration dict to migrate
        steps: Ordered list of migration steps to apply
        registry: Migration registry containing transform functions

    Returns:
        Migrated configuration dict
    """
    result = config_dict.copy()

    for step in steps:
        transform = registry.get_transform(step)
        result = transform(result)

    return result


# Global migration registry instance
_REGISTRY = MigrationRegistry()


def get_registry() -> MigrationRegistry:
    """Get the global migration registry.

    Returns:
        The global MigrationRegistry instance
    """
    return _REGISTRY


# Seed migration: 0.0.1 → 0.1.0
# This is the first real migration demonstrating the system.
def _migrate_0_0_1_to_0_1_0(config: ConfigDict) -> ConfigDict:
    """Migrate config from schema version 0.0.1 to 0.1.0.

    Changes:
    - Updates schema_version field from 0.0.1 to 0.1.0
    - Preserves all existing config fields (no data loss)

    Args:
        config: Config dict at version 0.0.1

    Returns:
        Config dict at version 0.1.0
    """
    migrated = config.copy()

    # Update schema version
    migrated["schema_version"] = "0.1.0"

    return migrated


# Register the seed migration
_REGISTRY.register(
    source_version=VersionInfo(major=0, minor=0, patch=1),
    target_version=VersionInfo(major=0, minor=1, patch=0),
    description="Initial migration demonstrating the migration system",
    transform_fn=_migrate_0_0_1_to_0_1_0,
)
