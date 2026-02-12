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


def test_global_version_exists() -> None:
    """Test global VERSION is defined and valid."""
    assert VERSION is not None
    assert str(VERSION) == "0.1.5"
