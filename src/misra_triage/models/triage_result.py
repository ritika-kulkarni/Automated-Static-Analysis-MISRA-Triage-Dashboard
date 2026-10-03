"""Triage report aggregates for CLI output and CI artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from misra_triage.models.violation import Violation


class TriageSummary(BaseModel):
    total: int = 0
    baseline: int = 0
    new: int = 0
    resolved: int = 0
    blocking_new: int = 0
    tickets_created: int = 0
    gate_passed: bool = True


class TriageReport(BaseModel):
    """Full triage outcome written as JSON for dashboards / CI."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tool_sources: list[str] = Field(default_factory=list)
    summary: TriageSummary = Field(default_factory=TriageSummary)
    new_violations: list[Violation] = Field(default_factory=list)
    baseline_violations: list[Violation] = Field(default_factory=list)
    resolved_violations: list[Violation] = Field(default_factory=list)
    blocking_violations: list[Violation] = Field(default_factory=list)
    jira_issues: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_dashboard_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "tool_sources": self.tool_sources,
            "summary": self.summary.model_dump(),
            "new_violations": [v.model_dump() for v in self.new_violations],
            "baseline_violations": [v.model_dump() for v in self.baseline_violations],
            "resolved_violations": [v.model_dump() for v in self.resolved_violations],
            "blocking_violations": [v.model_dump() for v in self.blocking_violations],
            "jira_issues": self.jira_issues,
            "errors": self.errors,
        }
