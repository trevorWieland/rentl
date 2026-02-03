"""Custom evaluators and report helpers for quality tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from pydantic_evals.evaluators import (
    EvaluationReason,
    EvaluationResult,
    Evaluator,
    EvaluatorContext,
)
from pydantic_evals.reporting import EvaluationReport

from tests.quality.agents.eval_types import AgentEvalOutput


def assert_report_success(report: EvaluationReport) -> None:
    """Assert a report has no failures and all assertions passed.

    Raises:
        AssertionError: If the report contains failures or failed assertions.
    """
    if report.failures:
        details = ", ".join(str(failure) for failure in report.failures)
        raise AssertionError(f"Eval failures detected: {details}")

    for case in report.cases:
        for name, assertion in case.assertions.items():
            if isinstance(assertion, (EvaluationResult, EvaluationReason)):
                value = assertion.value
                reason = assertion.reason
            else:
                value = assertion
                reason = None
            if value is not True:
                raise AssertionError(
                    f"Assertion failed: {case.name or 'case'}:{name} - "
                    f"{reason or 'No reason provided'}"
                )


def _get_output_data(output: object) -> dict[str, Any] | None:
    if isinstance(output, AgentEvalOutput):
        return output.output_data
    if isinstance(output, dict):
        data = cast(dict[str, Any], output).get("output_data")
        if isinstance(data, dict):
            return data
    return None


@dataclass
class OutputFieldPresent(Evaluator[Any, AgentEvalOutput]):
    """Ensure a field exists in output_data."""

    field_name: str

    def evaluate(self, ctx: EvaluatorContext[Any, AgentEvalOutput]) -> EvaluationReason:
        """Evaluate whether the field is present.

        Args:
            ctx: Evaluator context.

        Returns:
            Evaluation result with reason on failure.
        """
        output_data = _get_output_data(ctx.output)
        if output_data is None:
            return EvaluationReason(
                value=False,
                reason="Output data is unavailable",
            )
        present = self.field_name in output_data
        return EvaluationReason(
            value=present,
            reason=(None if present else f"Missing field: {self.field_name}"),
        )


@dataclass
class ListFieldMinLength(Evaluator[Any, AgentEvalOutput]):
    """Ensure a list field has at least the given length."""

    field_name: str
    min_length: int = 1

    def evaluate(self, ctx: EvaluatorContext[Any, AgentEvalOutput]) -> EvaluationReason:
        """Evaluate list length requirement.

        Args:
            ctx: Evaluator context.

        Returns:
            Evaluation result with reason on failure.
        """
        output_data = _get_output_data(ctx.output)
        if output_data is None:
            return EvaluationReason(
                value=False,
                reason="Output data is unavailable",
            )
        field = output_data.get(self.field_name)
        if not isinstance(field, list):
            return EvaluationReason(
                value=False,
                reason=f"Field {self.field_name} is not a list",
            )
        meets = len(field) >= self.min_length
        return EvaluationReason(
            value=meets,
            reason=(
                None if meets else f"Field {self.field_name} length < {self.min_length}"
            ),
        )


@dataclass
class ToolCallCountAtLeast(Evaluator[Any, AgentEvalOutput]):
    """Ensure at least N tool calls were recorded."""

    min_calls: int = 1

    def evaluate(self, ctx: EvaluatorContext[Any, AgentEvalOutput]) -> EvaluationReason:
        """Evaluate minimum tool call count.

        Args:
            ctx: Evaluator context.

        Returns:
            Evaluation result with reason on failure.
        """
        tool_calls = None
        if isinstance(ctx.output, AgentEvalOutput):
            tool_calls = ctx.output.tool_calls
        elif isinstance(ctx.output, dict):
            maybe_calls = ctx.output.get("tool_calls")
            if isinstance(maybe_calls, list):
                tool_calls = maybe_calls
        if tool_calls is None:
            return EvaluationReason(
                value=False,
                reason="Tool calls are unavailable",
            )
        count = len(tool_calls)
        meets = count >= self.min_calls
        return EvaluationReason(
            value=meets,
            reason=(
                None
                if meets
                else f"Expected >= {self.min_calls} tool calls, got {count}"
            ),
        )


@dataclass
class ToolResultHasKeys(Evaluator[Any, AgentEvalOutput]):
    """Ensure the first tool call contains required result keys."""

    required_keys: tuple[str, ...]

    def evaluate(self, ctx: EvaluatorContext[Any, AgentEvalOutput]) -> EvaluationReason:
        """Evaluate tool result key coverage.

        Args:
            ctx: Evaluator context.

        Returns:
            Evaluation result with reason on failure.
        """
        tool_calls = None
        if isinstance(ctx.output, AgentEvalOutput):
            tool_calls = ctx.output.tool_calls
        elif isinstance(ctx.output, dict):
            maybe_calls = ctx.output.get("tool_calls")
            if isinstance(maybe_calls, list):
                tool_calls = maybe_calls
        if not tool_calls:
            return EvaluationReason(
                value=False,
                reason="No tool calls recorded",
            )
        first_call = tool_calls[0]
        result = first_call.result if hasattr(first_call, "result") else None
        if not isinstance(result, dict):
            return EvaluationReason(
                value=False,
                reason="Tool call result is unavailable",
            )
        missing = [key for key in self.required_keys if key not in result]
        if missing:
            missing_text = ", ".join(missing)
            return EvaluationReason(
                value=False,
                reason=f"Missing tool result keys: {missing_text}",
            )
        return EvaluationReason(value=True, reason=None)
