"""Unit tests for primitive types and validators."""

from uuid import UUID, uuid4, uuid7

import pytest
from pydantic import TypeAdapter

from rentl_schemas.primitives import Uuid7


def test_uuid7_accepts_version_7() -> None:
    """Ensure Uuid7 validator accepts version 7 UUIDs."""
    # Generate a real UUID v7
    uuid_v7 = uuid7()
    assert uuid_v7.version == 7

    # Should validate without error using TypeAdapter
    adapter = TypeAdapter(Uuid7)
    validated = adapter.validate_python(uuid_v7)
    assert validated.version == 7


def test_uuid7_rejects_non_version_7() -> None:
    """Ensure Uuid7 validator rejects non-version-7 UUIDs."""
    # UUID v4 should be rejected
    uuid_v4 = uuid4()
    assert uuid_v4.version == 4

    adapter = TypeAdapter(Uuid7)
    with pytest.raises(ValueError, match="UUID must be version 7"):
        adapter.validate_python(uuid_v4)


def test_uuid7_rejects_version_1() -> None:
    """Ensure Uuid7 validator rejects UUID version 1."""
    # Create a UUID v1 manually (time-based)
    # We can't easily generate a real v1, so we'll construct one with version field set
    uuid_bytes = uuid4().bytes
    # Modify version bits to be version 1
    uuid_bytes_list = bytearray(uuid_bytes)
    uuid_bytes_list[6] = (uuid_bytes_list[6] & 0x0F) | 0x10  # Version 1
    uuid_v1 = UUID(bytes=bytes(uuid_bytes_list))

    adapter = TypeAdapter(Uuid7)
    with pytest.raises(ValueError, match="UUID must be version 7"):
        adapter.validate_python(uuid_v1)
