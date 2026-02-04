"""BDD step implementation functions for integration tests.

This package contains shared step implementation functions that should be
decorated in conftest.py files to register them with pytest-bdd.

Usage in conftest.py:
    from pytest_bdd import then, parsers
    from tests.integration.steps import (
        step_command_succeeds,
        step_command_returns_error,
        step_error_code_is,
    )

    # Register steps in this module's namespace
    then("the command succeeds")(step_command_succeeds)
    then("the command returns an error response")(step_command_returns_error)
    then(parsers.parse('the error code is "{error_code}"'))(step_error_code_is)
"""

from tests.integration.steps.cli_steps import (
    CliContextProtocol,
    step_command_returns_error,
    step_command_succeeds,
    step_error_code_is,
)

__all__ = [
    "CliContextProtocol",
    "step_command_returns_error",
    "step_command_succeeds",
    "step_error_code_is",
]
