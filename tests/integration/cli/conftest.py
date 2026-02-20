"""BDD step definitions shared across CLI integration tests.

This conftest applies pytest-bdd step decorators to shared step implementation
functions, registering them as fixtures in this module's namespace so they're
available to all test files in this directory.
"""

from pytest_bdd import parsers, then

from tests.integration.steps import (
    CliContextProtocol,
    step_command_returns_error,
    step_command_succeeds,
    step_error_code_is,
)


# Define a generic step that checks for command failure (non-zero exit code)
def step_command_fails(ctx: CliContextProtocol) -> None:
    """Assert the CLI command exits with non-zero code."""
    assert ctx.result is not None
    assert ctx.result.exit_code != 0, (
        f"Expected non-zero exit code, got {ctx.result.exit_code}"
    )


# Register shared step definitions in this conftest's namespace
# so they're available to all CLI tests
then("the command succeeds")(step_command_succeeds)
then("the command fails")(step_command_fails)
then("the command returns an error response")(step_command_returns_error)
then(parsers.parse('the error code is "{error_code}"'))(step_error_code_is)
