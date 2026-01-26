"""Version information and core types."""

from pydantic import Field

from rentl_schemas.base import BaseSchema


class VersionInfo(BaseSchema):
    """Application version information."""

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")

    def __str__(self) -> str:
        """Return semantic version string."""
        return f"{self.major}.{self.minor}.{self.patch}"
