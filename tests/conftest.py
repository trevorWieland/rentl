"""Common pytest configuration."""

from pathlib import Path

import anyio
import coverage
import pytest
from rentl_cli.utils.baseline import write_baseline


def pytest_sessionfinish(session: object, exitstatus: int) -> None:
    """Ensure coverage data connections are closed to avoid ResourceWarnings."""
    cov = coverage.Coverage.current()
    if cov is None:
        return

    data = cov.get_data()
    close = getattr(data, "close", None)
    if callable(close):
        close()

    collector = getattr(cov, "_collector", None)
    collector_data = getattr(collector, "data", None) if collector else None
    collector_close = getattr(collector_data, "close", None)
    if callable(collector_close):
        collector_close()


@pytest.fixture
def anyio_backend() -> str:
    """Force asyncio backend for anyio-powered tests.

    Returns:
        str: The backend name.
    """
    return "asyncio"


@pytest.fixture
async def tiny_vn_tmp(tmp_path: Path) -> Path:
    """Provision a fresh tiny_vn baseline into a temp directory for repeatable tests.

    Returns:
        Path: Path to the generated project root.
    """
    await write_baseline(tmp_path)
    # Ensure output/checkpoint dirs exist for tests using sqlite savers.
    await anyio.Path(tmp_path / ".rentl").mkdir(parents=True, exist_ok=True)
    return tmp_path
