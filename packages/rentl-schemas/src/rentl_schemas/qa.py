"""Quality assurance schemas for issues and summaries."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    IssueId,
    JsonValue,
    LineId,
    QaCategory,
    QaSeverity,
)


class QaIssue(BaseSchema):
    """A single QA issue discovered during validation."""

    issue_id: IssueId = Field(..., description="Unique QA issue identifier")
    line_id: LineId = Field(..., description="Line identifier associated with issue")
    category: QaCategory = Field(..., description="Issue category")
    severity: QaSeverity = Field(..., description="Issue severity")
    message: str = Field(..., min_length=1, description="Issue description")
    suggestion: str | None = Field(None, description="Suggested fix or remediation")
    metadata: dict[str, JsonValue] | None = Field(
        None, description="Additional structured metadata"
    )


class QaSummary(BaseSchema):
    """Aggregate QA summary for a phase or run."""

    total_issues: int = Field(..., ge=0, description="Total issue count")
    by_category: dict[QaCategory, int] = Field(
        ..., description="Issue counts by category"
    )
    by_severity: dict[QaSeverity, int] = Field(
        ..., description="Issue counts by severity"
    )


class ReviewerNote(BaseSchema):
    """Reviewer note attached to a line during QA or edit."""

    line_id: LineId = Field(..., description="Line identifier for the note")
    note: str = Field(..., min_length=1, description="Reviewer note text")
    author: str | None = Field(None, description="Reviewer identifier")


class LineEdit(BaseSchema):
    """Record of an edit applied to a translated line."""

    line_id: LineId = Field(..., description="Line identifier")
    original_text: str = Field(
        ..., min_length=1, description="Original translated text"
    )
    edited_text: str = Field(..., min_length=1, description="Edited text")
    reason: str | None = Field(None, description="Reason for the edit")
