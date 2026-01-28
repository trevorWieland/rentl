"""Tests for phase result summary schemas."""

from __future__ import annotations

import pytest

from rentl_schemas.primitives import PhaseName, QaCategory, QaSeverity
from rentl_schemas.qa import QaSummary
from rentl_schemas.results import (
    PhaseResultMetric,
    PhaseResultSummary,
    ResultMetricUnit,
)


@pytest.mark.unit
def test_phase_result_summary_accepts_valid_metrics() -> None:
    """PhaseResultSummary accepts valid metrics for a phase."""
    metric = PhaseResultMetric(
        metric_key="line_count",
        unit=ResultMetricUnit.LINES,
        value=12,
        notes=None,
    )
    summary = PhaseResultSummary(
        phase=PhaseName.INGEST,
        target_language=None,
        metrics=[metric],
        qa_summary=None,
        dimensions=None,
    )
    assert summary.metrics[0].metric_key == "line_count"


@pytest.mark.unit
def test_phase_result_summary_rejects_invalid_metric_key() -> None:
    """PhaseResultSummary rejects metric keys outside phase definitions."""
    metric = PhaseResultMetric(
        metric_key="issue_count",
        unit=ResultMetricUnit.ISSUES,
        value=1,
        notes=None,
    )
    with pytest.raises(ValueError):
        PhaseResultSummary(
            phase=PhaseName.INGEST,
            target_language=None,
            metrics=[metric],
            qa_summary=None,
            dimensions=None,
        )


@pytest.mark.unit
def test_phase_result_metric_ratio_bounds() -> None:
    """Ratio metrics must stay within 0..1."""
    with pytest.raises(ValueError):
        PhaseResultMetric(
            metric_key="annotation_coverage",
            unit=ResultMetricUnit.RATIO,
            value=1.1,
            notes=None,
        )


@pytest.mark.unit
def test_phase_result_metric_requires_whole_numbers_for_counts() -> None:
    """Non-ratio metrics must be whole numbers."""
    with pytest.raises(ValueError):
        PhaseResultMetric(
            metric_key="line_count",
            unit=ResultMetricUnit.LINES,
            value=1.5,
            notes=None,
        )


@pytest.mark.unit
def test_phase_result_summary_requires_qa_summary_for_qa() -> None:
    """QA summaries must include QaSummary when phase is QA."""
    metric = PhaseResultMetric(
        metric_key="issue_count",
        unit=ResultMetricUnit.ISSUES,
        value=0,
        notes=None,
    )
    with pytest.raises(ValueError):
        PhaseResultSummary(
            phase=PhaseName.QA,
            target_language="ja",
            metrics=[metric],
            qa_summary=None,
            dimensions=None,
        )
    qa_summary = QaSummary(
        total_issues=0,
        by_category=dict.fromkeys(QaCategory, 0),
        by_severity=dict.fromkeys(QaSeverity, 0),
    )
    summary = PhaseResultSummary(
        phase=PhaseName.QA,
        target_language="ja",
        metrics=[metric],
        qa_summary=qa_summary,
        dimensions=None,
    )
    assert summary.qa_summary is not None
