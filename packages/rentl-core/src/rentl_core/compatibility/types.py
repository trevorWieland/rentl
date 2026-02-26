"""Result types for compatibility verification."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import PhaseName


class PhaseVerificationStatus(StrEnum):
    """Outcome of verifying a single pipeline phase."""

    PASSED = "passed"
    FAILED = "failed"


class PhaseResult(BaseSchema):
    """Result of running one pipeline phase during verification."""

    phase: PhaseName = Field(..., description="Pipeline phase that was verified")
    status: PhaseVerificationStatus = Field(
        ..., description="Whether the phase passed or failed"
    )
    error_message: str | None = Field(
        None, description="Actionable error message when status is failed"
    )


class ModelVerificationResult(BaseSchema):
    """Result of verifying a single model through the mini-pipeline."""

    model_id: str = Field(
        ..., min_length=1, description="Model identifier that was verified"
    )
    passed: bool = Field(..., description="Whether all phases passed")
    phase_results: list[PhaseResult] = Field(
        ..., description="Per-phase verification results"
    )


class RegistryVerificationResult(BaseSchema):
    """Result of verifying all models in a registry."""

    passed: bool = Field(..., description="Whether all models passed verification")
    model_results: list[ModelVerificationResult] = Field(
        ..., description="Per-model verification results"
    )
