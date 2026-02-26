"""Compatibility verification runner for multi-model testing."""

from rentl_core.compatibility.loader import load_lm_studio_model
from rentl_core.compatibility.runner import (
    GOLDEN_SOURCE_LINE,
    PHASE_CONFIGS,
    verify_model,
    verify_registry,
)
from rentl_core.compatibility.types import (
    ModelVerificationResult,
    PhaseResult,
    PhaseVerificationStatus,
    RegistryVerificationResult,
)

__all__ = [
    "GOLDEN_SOURCE_LINE",
    "PHASE_CONFIGS",
    "ModelVerificationResult",
    "PhaseResult",
    "PhaseVerificationStatus",
    "RegistryVerificationResult",
    "load_lm_studio_model",
    "verify_model",
    "verify_registry",
]
