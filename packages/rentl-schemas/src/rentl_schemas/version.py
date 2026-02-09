"""Version information and core types."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema

# Current schema version for rentl.toml config files
CURRENT_SCHEMA_VERSION = (0, 1, 0)


class VersionInfo(BaseSchema):
    """Application version information."""

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")

    def __str__(self) -> str:
        """Return semantic version string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def _as_tuple(self) -> tuple[int, int, int]:
        """Return version as tuple for comparison."""
        return (self.major, self.minor, self.patch)

    def __lt__(self, other: object) -> bool:
        """Compare if this version is less than another.

        Returns:
            True if this version is less than other, False otherwise.
        """
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self._as_tuple() < other._as_tuple()

    def __le__(self, other: object) -> bool:
        """Compare if this version is less than or equal to another.

        Returns:
            True if this version is less than or equal to other, False otherwise.
        """
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self._as_tuple() <= other._as_tuple()

    def __eq__(self, other: object) -> bool:
        """Compare if this version equals another.

        Returns:
            True if versions are equal, False otherwise.
        """
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self._as_tuple() == other._as_tuple()

    def __gt__(self, other: object) -> bool:
        """Compare if this version is greater than another.

        Returns:
            True if this version is greater than other, False otherwise.
        """
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self._as_tuple() > other._as_tuple()

    def __ge__(self, other: object) -> bool:
        """Compare if this version is greater than or equal to another.

        Returns:
            True if this version is greater than or equal to other, False otherwise.
        """
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return self._as_tuple() >= other._as_tuple()

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts."""
        return hash(self._as_tuple())
