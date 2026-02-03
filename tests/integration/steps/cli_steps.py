"""Shared BDD step implementation functions for CLI integration tests.

This module provides reusable step implementation functions that can be
decorated with pytest-bdd step decorators in conftest.py files.

Note: These functions are NOT decorated here because pytest-bdd registers
step fixtures in the caller's module namespace. To share step definitions
across test modules, import these functions and apply decorators in conftest.py.

Example usage in conftest.py:
    from pytest_bdd import then, parsers
    from tests.integration.steps.cli_steps import (
        step_command_succeeds,
        step_command_returns_error,
        step_error_code_is,
    )

    then("the command succeeds")(step_command_succeeds)
    then("the command returns an error response")(step_command_returns_error)
    then(parsers.parse('the error code is "{error_code}"'))(step_error_code_is)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from click.testing import Result

if TYPE_CHECKING:
    pass


class CliContextProtocol(Protocol):
    """Protocol for CLI test contexts that have a result and response."""

    result: Result | None
    response: dict | None


def step_command_succeeds(ctx: CliContextProtocol) -> None:
    """Assert the CLI command exits with code 0."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}: {ctx.result.stdout}"
    )


def step_command_returns_error(ctx: CliContextProtocol) -> None:
    """Assert the command returns an error response (exit 0 but error in JSON)."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0  # CLI exits 0 but returns error in JSON
    assert ctx.response is not None
    assert ctx.response.get("error") is not None


def step_error_code_is(ctx: CliContextProtocol, error_code: str) -> None:
    """Assert the error response has the expected code."""
    assert ctx.response is not None
    assert ctx.response["error"] is not None
    assert ctx.response["error"]["code"] == error_code
