"""Token test to verify llm_live gating and env plumbing."""

from __future__ import annotations

import pytest


@pytest.mark.llm_live
def test_llm_live_gate_enforced(llm_judge_model: str) -> None:
    """Runs only when live LLM env is configured; otherwise skipped by conftest."""
    assert llm_judge_model, "Expected LLM model from environment"
