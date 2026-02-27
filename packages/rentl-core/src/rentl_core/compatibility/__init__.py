"""Compatibility verification runner for multi-model testing."""

from rentl_core.compatibility.loader import (
    ModelUnloadError,
    list_lm_studio_models,
    load_lm_studio_model,
    unload_lm_studio_model,
)
from rentl_core.compatibility.runner import (
    GOLDEN_SOURCE_LINE,
    PHASE_CONFIGS,
    verify_model,
    verify_registry,
    verify_single_phase,
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
    "ModelUnloadError",
    "ModelVerificationResult",
    "PhaseResult",
    "PhaseVerificationStatus",
    "RegistryVerificationResult",
    "list_lm_studio_models",
    "load_lm_studio_model",
    "unload_lm_studio_model",
    "verify_model",
    "verify_registry",
    "verify_single_phase",
]
