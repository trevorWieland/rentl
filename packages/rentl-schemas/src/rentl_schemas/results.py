"""Result summary schemas for completed pipeline phases."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import EVENT_NAME_PATTERN, LanguageCode, PhaseName
from rentl_schemas.qa import QaSummary

type ResultMetricKey = Annotated[str, Field(pattern=EVENT_NAME_PATTERN)]


class ResultMetricUnit(StrEnum):
    """Units for phase result metrics."""

    COUNT = "count"
    LINES = "lines"
    SCENES = "scenes"
    ROUTES = "routes"
    TERMS = "terms"
    NOTES = "notes"
    ISSUES = "issues"
    EDITS = "edits"
    CHARACTERS = "characters"
    COLUMNS = "columns"
    RATIO = "ratio"


PHASE_RESULT_METRIC_DEFINITIONS: dict[
    PhaseName, dict[ResultMetricKey, ResultMetricUnit]
] = {
    PhaseName.INGEST: {
        "line_count": ResultMetricUnit.LINES,
        "scene_count": ResultMetricUnit.SCENES,
        "route_count": ResultMetricUnit.ROUTES,
    },
    PhaseName.CONTEXT: {
        "scene_summary_count": ResultMetricUnit.SCENES,
        "context_note_count": ResultMetricUnit.NOTES,
        "glossary_term_count": ResultMetricUnit.TERMS,
        "character_count": ResultMetricUnit.CHARACTERS,
    },
    PhaseName.PRETRANSLATION: {
        "annotation_count": ResultMetricUnit.COUNT,
        "annotated_line_count": ResultMetricUnit.LINES,
        "annotation_coverage": ResultMetricUnit.RATIO,
        "term_candidate_count": ResultMetricUnit.TERMS,
    },
    PhaseName.TRANSLATE: {
        "translated_line_count": ResultMetricUnit.LINES,
    },
    PhaseName.QA: {
        "issue_count": ResultMetricUnit.ISSUES,
    },
    PhaseName.EDIT: {
        "edited_line_count": ResultMetricUnit.LINES,
        "change_count": ResultMetricUnit.EDITS,
        "changed_line_count": ResultMetricUnit.LINES,
    },
    PhaseName.EXPORT: {
        "exported_line_count": ResultMetricUnit.LINES,
        "untranslated_line_count": ResultMetricUnit.LINES,
        "column_count": ResultMetricUnit.COLUMNS,
    },
}


class PhaseResultDimension(BaseSchema):
    """Optional dimension label for phase result metrics."""

    key: ResultMetricKey = Field(..., description="Dimension key in snake_case")
    value: str = Field(..., min_length=1, description="Dimension value")


class PhaseResultMetric(BaseSchema):
    """Single metric entry for a phase result summary."""

    metric_key: ResultMetricKey = Field(
        ..., description="Metric identifier in snake_case"
    )
    unit: ResultMetricUnit = Field(..., description="Metric unit")
    value: int | float = Field(..., ge=0, description="Metric value")
    notes: str | None = Field(None, description="Optional metric notes")

    @model_validator(mode="after")
    def _validate_metric_value(self) -> PhaseResultMetric:
        if self.unit == ResultMetricUnit.RATIO:
            if self.value > 1:
                raise ValueError("ratio metrics must be between 0 and 1")
            return self
        if isinstance(self.value, float) and not self.value.is_integer():
            raise ValueError("non-ratio metrics must be whole numbers")
        return self


class PhaseResultSummary(BaseSchema):
    """Summary metrics for a completed phase run."""

    phase: PhaseName = Field(..., description="Phase name")
    target_language: LanguageCode | None = Field(
        None, description="Target language if applicable"
    )
    metrics: list[PhaseResultMetric] = Field(
        ..., min_length=1, description="Phase result metrics"
    )
    qa_summary: QaSummary | None = Field(
        None, description="QA summary for QA phase outputs"
    )
    dimensions: list[PhaseResultDimension] | None = Field(
        None, description="Optional metric dimensions"
    )

    @model_validator(mode="after")
    def _validate_summary(self) -> PhaseResultSummary:
        allowed = PHASE_RESULT_METRIC_DEFINITIONS.get(self.phase)
        if allowed is None:
            raise ValueError("metrics are not defined for this phase")
        seen_keys: set[str] = set()
        for metric in self.metrics:
            if metric.metric_key in seen_keys:
                raise ValueError("metric_key values must be unique per phase")
            seen_keys.add(metric.metric_key)
            expected_unit = allowed.get(metric.metric_key)
            if expected_unit is None:
                raise ValueError("metric_key is not allowed for this phase")
            if metric.unit != expected_unit:
                raise ValueError("metric unit does not match phase definition")
        if self.phase == PhaseName.QA and self.qa_summary is None:
            raise ValueError("qa_summary is required for QA phase summaries")
        if self.phase != PhaseName.QA and self.qa_summary is not None:
            raise ValueError("qa_summary is only allowed for QA phase summaries")
        if self.dimensions is not None:
            seen_dimensions: set[str] = set()
            for dimension in self.dimensions:
                if dimension.key in seen_dimensions:
                    raise ValueError("dimension keys must be unique")
                seen_dimensions.add(dimension.key)
        return self
