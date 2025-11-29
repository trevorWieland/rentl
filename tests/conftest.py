"""Common pytest configuration."""

import os
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


# ---- Live LLM gating and helpers ----
def _has_llm_env() -> bool:
    """Return True when live LLM tests are explicitly enabled and required settings are present."""
    if os.getenv("RENTL_LLM_TESTS") != "1":
        return False
    try:
        from rentl_core.config.settings import get_settings
    except Exception:
        return False

    try:
        settings = get_settings()
    except Exception:
        return False

    return bool(settings.openai_url) and bool(settings.openai_api_key.get_secret_value()) and bool(settings.llm_model)


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "llm_live: opt-in tests that call real LLMs; require RENTL_LLM_TESTS=1 and OPENAI_* env vars.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip llm_live tests unless env is set."""
    if _has_llm_env():
        return

    skip_reason = (
        "Skipped llm_live test (set RENTL_LLM_TESTS=1 and provide OPENAI_URL, OPENAI_API_KEY, LLM_MODEL to enable)"
    )
    skip_marker = pytest.mark.skip(reason=skip_reason)
    for item in items:
        if "llm_live" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture
def llm_judge_model() -> str:
    """Return the configured LLM model for agentevals judges."""
    if not _has_llm_env():
        pytest.skip("Live LLM env not configured")
    from rentl_core.config.settings import get_settings

    settings = get_settings()
    return settings.llm_model
