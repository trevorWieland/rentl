"""Unit tests for compatibility verification result types."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rentl_core.compatibility.types import (
    ModelVerificationResult,
    PhaseResult,
    PhaseVerificationStatus,
    RegistryVerificationResult,
)
from rentl_schemas.primitives import PhaseName


def test_phase_result_passed() -> None:
    """PhaseResult captures a successful phase verification."""
    result = PhaseResult(
        phase=PhaseName.CONTEXT,
        status=PhaseVerificationStatus.PASSED,
        error_message=None,
    )
    assert result.phase == "context"
    assert result.status == "passed"
    assert result.error_message is None


def test_phase_result_failed_with_message() -> None:
    """PhaseResult captures a failed phase with error details."""
    result = PhaseResult(
        phase=PhaseName.TRANSLATE,
        status=PhaseVerificationStatus.FAILED,
        error_message="Structured output validation failed",
    )
    assert result.status == "failed"
    assert "Structured output" in (result.error_message or "")


def test_model_verification_result_all_passed() -> None:
    """ModelVerificationResult reports passed when all phases pass."""
    result = ModelVerificationResult(
        model_id="qwen/qwen3.5-27b",
        passed=True,
        phase_results=[
            PhaseResult(
                phase=PhaseName.CONTEXT,
                status=PhaseVerificationStatus.PASSED,
            ),
        ],
    )
    assert result.passed is True


def test_model_verification_result_rejects_empty_model_id() -> None:
    """model_id must be non-empty."""
    with pytest.raises(ValidationError):
        ModelVerificationResult(
            model_id="",
            passed=True,
            phase_results=[],
        )


def test_registry_verification_result() -> None:
    """RegistryVerificationResult aggregates model results."""
    result = RegistryVerificationResult(
        passed=False,
        model_results=[
            ModelVerificationResult(
                model_id="model-a",
                passed=True,
                phase_results=[],
            ),
            ModelVerificationResult(
                model_id="model-b",
                passed=False,
                phase_results=[
                    PhaseResult(
                        phase=PhaseName.QA,
                        status=PhaseVerificationStatus.FAILED,
                        error_message="QA check failed",
                    ),
                ],
            ),
        ],
    )
    assert result.passed is False
    assert len(result.model_results) == 2
