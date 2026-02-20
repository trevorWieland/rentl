"""Unit tests for rentl-core version module."""

from rentl_core import VERSION
from rentl_schemas.version import VersionInfo


def test_version_info_creation() -> None:
    """Test VersionInfo can be created with valid values."""
    info = VersionInfo(major=1, minor=2, patch=3)
    assert info.major == 1
    assert info.minor == 2
    assert info.patch == 3


def test_version_info_str() -> None:
    """Test VersionInfo string representation."""
    info = VersionInfo(major=1, minor=2, patch=3)
    assert str(info) == "1.2.3"


def test_global_version_is_valid_version_info() -> None:
    """Test global VERSION is a valid VersionInfo with non-negative components."""
    assert isinstance(VERSION, VersionInfo)
    assert VERSION.major >= 0
    assert VERSION.minor >= 0
    assert VERSION.patch >= 0
    assert str(VERSION) == f"{VERSION.major}.{VERSION.minor}.{VERSION.patch}"
