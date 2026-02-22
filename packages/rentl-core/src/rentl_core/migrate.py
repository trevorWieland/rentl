"""Config migration registry and engine for schema versioning."""

from __future__ import annotations

import contextlib
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rentl_schemas.migration import MigrationStep
from rentl_schemas.version import CURRENT_SCHEMA_VERSION, VersionInfo

# Type alias for valid TOML value types (recursive for nested structures)
type ConfigValue = (
    str | int | float | bool | list["ConfigValue"] | dict[str, "ConfigValue"]
)

# Type alias for config dictionary (unstructured TOML data)
type ConfigDict = dict[str, ConfigValue]

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
    - Updates project.schema_version field from 0.0.1 to 0.1.0
    - Preserves all existing config fields (no data loss)

    Args:
        config: Config dict at version 0.0.1

    Returns:
        Config dict at version 0.1.0
    """
    migrated = config.copy()

    # Update schema version in project section
    if "project" not in migrated:
        migrated["project"] = {}

    # Deep copy project section if it exists to avoid mutation
    if isinstance(migrated["project"], dict):
        migrated["project"] = dict(migrated["project"])
        migrated["project"]["schema_version"] = {
            "major": 0,
            "minor": 1,
            "patch": 0,
        }

    return migrated


def dict_to_toml(data: ConfigDict) -> str:
    """Convert a config dictionary to TOML format string.

    Simple TOML serializer that handles the subset of TOML used in rentl configs.
    Supports nested tables, strings, integers, floats, booleans, and arrays.

    Args:
        data: Dictionary to serialize to TOML

    Returns:
        TOML-formatted string
    """
    lines: list[str] = []

    def _write_value(value: ConfigValue) -> str:
        """Serialize a single value to TOML format.

        Returns:
            TOML-formatted string representation of the value
        """
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, int | float):
            return str(value)
        elif isinstance(value, str):
            # Escape quotes and backslashes
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(value, list):
            items = [_write_value(item) for item in value]
            return f"[{', '.join(items)}]"
        elif isinstance(value, dict):
            # Inline table
            items = [f"{k} = {_write_value(v)}" for k, v in value.items()]
            return f"{{ {', '.join(items)} }}"
        else:
            return str(value)

    def _write_table(table_data: dict, prefix: str = "") -> None:
        """Recursively write tables and their contents."""
        # Separate simple values from nested tables
        simple_keys = []
        table_keys = []

        for key, value in table_data.items():
            if isinstance(value, dict) and not all(
                isinstance(v, int | float | str | bool) for v in value.values()
            ):
                table_keys.append(key)
            else:
                simple_keys.append(key)

        # Write simple key-value pairs
        if simple_keys:
            if prefix:
                lines.append(f"[{prefix}]")
            for key in simple_keys:
                value = table_data[key]
                lines.append(f"{key} = {_write_value(value)}")
            if table_keys:
                lines.append("")  # Blank line before nested tables

        # Write nested tables
        for key in table_keys:
            value = table_data[key]
            new_prefix = f"{prefix}.{key}" if prefix else key
            _write_table(value, new_prefix)
            lines.append("")  # Blank line between tables

    _write_table(data)

    # Remove trailing blank lines
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines) + "\n"


@dataclass
class MigrateResult:
    """Result of a config migration operation."""

    current_version: VersionInfo
    target_version: VersionInfo
    steps: list[MigrationStep] = field(default_factory=list)
    up_to_date: bool = False
    dry_run: bool = False
    backup_path: Path | None = None


class MigrateError(Exception):
    """Raised when a config migration operation fails."""


def migrate_config(
    config_path: Path,
    *,
    dry_run: bool = False,
    registry: MigrationRegistry | None = None,
) -> MigrateResult:
    """Run the full config migration workflow: load, plan, apply, backup, write.

    Args:
        config_path: Path to the rentl.toml config file
        dry_run: If True, plan only without writing changes
        registry: Migration registry to use (defaults to global registry)

    Returns:
        MigrateResult with migration details

    Raises:
        MigrateError: If config cannot be loaded, parsed, or migrated
    """
    if registry is None:
        registry = get_registry()

    # Load TOML config
    if not config_path.exists():
        raise MigrateError(f"Config file not found: {config_path}")

    try:
        with config_path.open("rb") as config_file:
            config_data = tomllib.load(config_file)
    except Exception as exc:
        raise MigrateError(f"Failed to parse config: {exc}") from exc

    # Extract current schema version
    project_data = config_data.get("project", {})
    if not isinstance(project_data, dict):
        raise MigrateError(
            "Invalid config: 'project' must be a table, "
            f"got {type(project_data).__name__}"
        )
    schema_version_data = project_data.get("schema_version")
    if not schema_version_data:
        raise MigrateError("No schema_version field found in config")

    try:
        current_version = VersionInfo(
            major=schema_version_data.get("major", 0),
            minor=schema_version_data.get("minor", 0),
            patch=schema_version_data.get("patch", 0),
        )
    except Exception as exc:
        raise MigrateError(f"Invalid schema_version format: {exc}") from exc

    # Get target version
    target_version = VersionInfo(
        major=CURRENT_SCHEMA_VERSION[0],
        minor=CURRENT_SCHEMA_VERSION[1],
        patch=CURRENT_SCHEMA_VERSION[2],
    )

    # Plan migrations
    try:
        migration_steps = plan_migrations(current_version, target_version, registry)
    except ValueError as exc:
        raise MigrateError(str(exc)) from exc

    # Already up to date
    if not migration_steps:
        return MigrateResult(
            current_version=current_version,
            target_version=target_version,
            up_to_date=True,
        )

    # Dry-run: return plan without applying
    if dry_run:
        return MigrateResult(
            current_version=current_version,
            target_version=target_version,
            steps=migration_steps,
            dry_run=True,
        )

    # Apply migrations
    try:
        migrated_config = apply_migrations(config_data, migration_steps, registry)
    except Exception as exc:
        raise MigrateError(f"Migration failed: {exc}") from exc

    # Back up original config
    backup_path = config_path.with_suffix(".toml.bak")
    try:
        backup_path.write_bytes(config_path.read_bytes())
    except Exception as exc:
        raise MigrateError(f"Failed to create backup: {exc}") from exc

    # Write migrated config
    try:
        migrated_toml = dict_to_toml(migrated_config)
        config_path.write_text(migrated_toml, encoding="utf-8")
    except Exception as exc:
        # Attempt to restore from backup
        with contextlib.suppress(Exception):
            config_path.write_bytes(backup_path.read_bytes())
        raise MigrateError(f"Failed to write migrated config: {exc}") from exc

    return MigrateResult(
        current_version=current_version,
        target_version=target_version,
        steps=migration_steps,
        backup_path=backup_path,
    )


def auto_migrate_config(
    config_dict: ConfigDict,
    target_version: VersionInfo,
    *,
    registry: MigrationRegistry | None = None,
) -> tuple[ConfigDict, bool]:
    """Auto-migrate a config dict to the target version if needed.

    Detects the current schema version from the config, plans migrations,
    and applies them. Returns the migrated config and a flag indicating
    whether migration occurred.

    Args:
        config_dict: Configuration dict to potentially migrate
        target_version: Target schema version to migrate to
        registry: Migration registry to use (defaults to global registry)

    Returns:
        Tuple of (migrated_config, was_migrated) where was_migrated is True
        if migration occurred, False if already up to date
    """
    if registry is None:
        registry = get_registry()

    # Extract current schema version from config
    try:
        project_data = config_dict.get("project")
        if not isinstance(project_data, dict):
            # No project section or invalid format — skip migration
            return (config_dict, False)

        schema_version_data = project_data.get("schema_version")
        if not schema_version_data or not isinstance(schema_version_data, dict):
            # No schema_version field or invalid format — skip migration
            return (config_dict, False)

        current_version = VersionInfo(
            major=int(schema_version_data.get("major", 0)),
            minor=int(schema_version_data.get("minor", 0)),
            patch=int(schema_version_data.get("patch", 0)),
        )
    except TypeError, ValueError:
        # Invalid schema_version format — skip migration
        return (config_dict, False)

    # Check if migration is needed
    if current_version >= target_version:
        return (config_dict, False)

    # Plan migrations
    migration_steps = plan_migrations(current_version, target_version, registry)

    if not migration_steps:
        return (config_dict, False)

    # Apply migrations
    migrated_config = apply_migrations(config_dict, migration_steps, registry)

    return (migrated_config, True)


@dataclass
class AutoMigrateResult:
    """Result of an auto-migration check on a loaded config."""

    config_dict: ConfigDict
    migrated: bool = False
    current_version: VersionInfo | None = None
    target_version: VersionInfo | None = None
    backup_path: Path | None = None


def auto_migrate_file(
    config_path: Path,
    config_dict: ConfigDict,
    *,
    registry: MigrationRegistry | None = None,
) -> AutoMigrateResult:
    """Auto-migrate a loaded config dict and persist changes to disk if needed.

    Detects the current schema version from the config, plans migrations,
    applies them, backs up the original file, and writes the migrated config.
    Pure business logic — no console output.

    Args:
        config_path: Path to the config file (for backup and write)
        config_dict: Already-loaded config dict
        registry: Migration registry to use (defaults to global registry)

    Returns:
        AutoMigrateResult with migrated dict and metadata

    Raises:
        MigrateError: If migration planning, application, backup, or write fails
    """
    if registry is None:
        registry = get_registry()

    target_version = VersionInfo(
        major=CURRENT_SCHEMA_VERSION[0],
        minor=CURRENT_SCHEMA_VERSION[1],
        patch=CURRENT_SCHEMA_VERSION[2],
    )

    migrated_dict, was_migrated = auto_migrate_config(
        config_dict, target_version, registry=registry
    )

    if not was_migrated:
        return AutoMigrateResult(config_dict=config_dict)

    # Extract current version for result metadata
    project_data = config_dict.get("project", {})
    schema_version_data = (
        project_data.get("schema_version", {}) if isinstance(project_data, dict) else {}
    )
    current_version = VersionInfo(
        major=int(schema_version_data.get("major", 0))
        if isinstance(schema_version_data, dict)
        else 0,
        minor=int(schema_version_data.get("minor", 0))
        if isinstance(schema_version_data, dict)
        else 0,
        patch=int(schema_version_data.get("patch", 0))
        if isinstance(schema_version_data, dict)
        else 0,
    )

    # Back up original config
    backup_path = config_path.with_suffix(".toml.bak")
    try:
        backup_path.write_bytes(config_path.read_bytes())
    except Exception as exc:
        raise MigrateError(f"Failed to create backup: {exc}") from exc

    # Write migrated config
    try:
        migrated_toml = dict_to_toml(migrated_dict)
        config_path.write_text(migrated_toml, encoding="utf-8")
    except Exception as exc:
        # Attempt to restore from backup
        with contextlib.suppress(Exception):
            config_path.write_bytes(backup_path.read_bytes())
        raise MigrateError(f"Failed to write migrated config: {exc}") from exc

    return AutoMigrateResult(
        config_dict=migrated_dict,
        migrated=True,
        current_version=current_version,
        target_version=target_version,
        backup_path=backup_path,
    )


# Register the seed migration
_REGISTRY.register(
    source_version=VersionInfo(major=0, minor=0, patch=1),
    target_version=VersionInfo(major=0, minor=1, patch=0),
    description="Initial migration demonstrating the migration system",
    transform_fn=_migrate_0_0_1_to_0_1_0,
)
