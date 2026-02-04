"""BDD step definitions shared across CLI integration tests.

This conftest applies pytest-bdd step decorators to shared step implementation
functions, registering them as fixtures in this module's namespace so they're
available to all test files in this directory.
"""

from pytest_bdd import parsers, then

from tests.integration.steps import (
    step_command_returns_error,
    step_command_succeeds,
    step_error_code_is,
)

# Register shared step definitions in this conftest's namespace
# so they're available to all CLI tests
then("the command succeeds")(step_command_succeeds)
then("the command returns an error response")(step_command_returns_error)
then(parsers.parse('the error code is "{error_code}"'))(step_error_code_is)
