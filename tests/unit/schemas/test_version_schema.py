"""Unit tests for VersionInfo and schema version constants."""

import pytest

from rentl_schemas.version import CURRENT_SCHEMA_VERSION, VersionInfo


def test_version_info_string_representation() -> None:
    """Ensure VersionInfo converts to semantic version string."""
    version = VersionInfo(major=1, minor=2, patch=3)
    assert str(version) == "1.2.3"


def test_version_info_tuple_conversion() -> None:
    """Ensure VersionInfo converts to tuple for comparison."""
    version = VersionInfo(major=1, minor=2, patch=3)
    assert version._as_tuple() == (1, 2, 3)


def test_version_info_less_than() -> None:
    """Test less-than comparison between versions."""
    v1 = VersionInfo(major=0, minor=1, patch=0)
    v2 = VersionInfo(major=0, minor=2, patch=0)
    v3 = VersionInfo(major=1, minor=0, patch=0)

    assert v1 < v2
    assert v2 < v3
    assert v1 < v3
    assert not (v2 < v1)
    assert not (v3 < v2)


def test_version_info_less_than_or_equal() -> None:
    """Test less-than-or-equal comparison between versions."""
    v1 = VersionInfo(major=0, minor=1, patch=0)
    v2 = VersionInfo(major=0, minor=1, patch=0)
    v3 = VersionInfo(major=0, minor=2, patch=0)

    assert v1 <= v2
    assert v1 <= v3
    assert v2 <= v3
    assert not (v3 <= v1)


def test_version_info_equal() -> None:
    """Test equality comparison between versions."""
    v1 = VersionInfo(major=1, minor=2, patch=3)
    v2 = VersionInfo(major=1, minor=2, patch=3)
    v3 = VersionInfo(major=1, minor=2, patch=4)

    assert v1 == v2
    assert v1 != v3


def test_version_info_greater_than() -> None:
    """Test greater-than comparison between versions."""
    v1 = VersionInfo(major=0, minor=2, patch=0)
    v2 = VersionInfo(major=0, minor=1, patch=0)
    v3 = VersionInfo(major=1, minor=0, patch=0)

    assert v1 > v2
    assert v3 > v1
    assert v3 > v2
    assert not (v2 > v1)
    assert not (v1 > v3)


def test_version_info_greater_than_or_equal() -> None:
    """Test greater-than-or-equal comparison between versions."""
    v1 = VersionInfo(major=0, minor=2, patch=0)
    v2 = VersionInfo(major=0, minor=2, patch=0)
    v3 = VersionInfo(major=0, minor=1, patch=0)

    assert v1 >= v2
    assert v1 >= v3
    assert v2 >= v3
    assert not (v3 >= v1)


def test_version_info_hash() -> None:
    """Test that VersionInfo can be hashed for use in sets and dicts."""
    v1 = VersionInfo(major=1, minor=2, patch=3)
    v2 = VersionInfo(major=1, minor=2, patch=3)
    v3 = VersionInfo(major=1, minor=2, patch=4)

    # Equal versions should have the same hash
    assert hash(v1) == hash(v2)
    # Different versions should (very likely) have different hashes
    assert hash(v1) != hash(v3)

    # Can be used in sets
    version_set = {v1, v2, v3}
    assert len(version_set) == 2  # v1 and v2 are equal


def test_version_info_comparison_with_non_version() -> None:
    """Test that comparing with non-VersionInfo types returns NotImplemented."""
    version = VersionInfo(major=1, minor=2, patch=3)

    # These should raise TypeError when compared with non-VersionInfo
    with pytest.raises(TypeError):
        _ = version < "1.2.3"  # ty: ignore[unsupported-operator]

    with pytest.raises(TypeError):
        _ = version <= 123  # ty: ignore[unsupported-operator]

    with pytest.raises(TypeError):
        _ = version > (1, 2, 3)  # ty: ignore[unsupported-operator]

    with pytest.raises(TypeError):
        _ = version >= [1, 2, 3]  # ty: ignore[unsupported-operator]


def test_version_info_equality_with_non_version_notimplemented() -> None:
    """Test that __eq__ with non-VersionInfo returns NotImplemented."""
    version = VersionInfo(major=1, minor=2, patch=3)

    # Calling __eq__ directly should return NotImplemented for non-VersionInfo
    # This allows Python to try the reverse comparison
    result = version.__eq__("1.2.3")  # noqa: PLC2801  # ty: ignore[invalid-argument-type]
    assert result == NotImplemented

    result = version.__eq__(123)  # noqa: PLC2801  # ty: ignore[invalid-argument-type]
    assert result == NotImplemented


def test_current_schema_version_constant() -> None:
    """Ensure CURRENT_SCHEMA_VERSION is defined as a tuple."""
    assert isinstance(CURRENT_SCHEMA_VERSION, tuple)
    assert len(CURRENT_SCHEMA_VERSION) == 3
    assert all(isinstance(x, int) for x in CURRENT_SCHEMA_VERSION)
    # Should be non-negative
    assert all(x >= 0 for x in CURRENT_SCHEMA_VERSION)


def test_version_ordering_patch_differences() -> None:
    """Test that patch version differences are correctly ordered."""
    v1 = VersionInfo(major=1, minor=2, patch=3)
    v2 = VersionInfo(major=1, minor=2, patch=4)
    v3 = VersionInfo(major=1, minor=2, patch=5)

    assert v1 < v2 < v3
    assert v3 > v2 > v1


def test_version_ordering_minor_differences() -> None:
    """Test that minor version differences are correctly ordered."""
    v1 = VersionInfo(major=1, minor=1, patch=99)
    v2 = VersionInfo(major=1, minor=2, patch=0)

    assert v1 < v2


def test_version_ordering_major_differences() -> None:
    """Test that major version differences are correctly ordered."""
    v1 = VersionInfo(major=0, minor=99, patch=99)
    v2 = VersionInfo(major=1, minor=0, patch=0)

    assert v1 < v2
