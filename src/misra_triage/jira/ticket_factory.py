"""Build categorized Jira issue payloads from violations."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from misra_triage.models.config import JiraConfig
from misra_triage.models.violation import Violation


class TicketFactory:
    """
    Groups new violations by (swc_module, owner, doors_req_id, misra_category)
    so each SWC owner receives a single categorized ticket per drop.
    """

    def __init__(self, config: JiraConfig) -> None:
        self.config = config

    def build_issues(self, violations: list[Violation]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str, str, str], list[Violation]] = defaultdict(list)
        for violation in violations:
            key = (
                violation.swc_module or "UNKNOWN_SWC",
                violation.owner or "unassigned",
                violation.doors_req_id or "NO-DOORS",
                violation.misra_category.value,
            )
            groups[key].append(violation)

        issues: list[dict[str, Any]] = []
        for (swc, owner, doors_id, category), items in sorted(groups.items()):
            issues.append(self._build_issue(swc, owner, doors_id, category, items))
        return issues

    def _build_issue(
        self,
        swc: str,
        owner: str,
        doors_id: str,
        category: str,
        items: list[Violation],
    ) -> dict[str, Any]:
        blocking = sum(1 for v in items if v.is_blocking)
        summary = (
            f"[MISRA Triage] {swc}: {len(items)} new {category} violation(s) "
            f"({blocking} blocking) — {doors_id}"
        )
        lines = [
            "h3. Automated MISRA / Static Analysis Triage",
            f"*SWC Module:* {swc}",
            f"*Owner:* {owner}",
            f"*DOORS Requirement:* {doors_id}",
            f"*MISRA Category:* {category}",
            f"*Count:* {len(items)} (blocking: {blocking})",
            "",
            "||Rule||File||Line||ASIL||Severity||Message||",
        ]
        for v in items[:50]:
            msg = (v.message or "").replace("|", "/").replace("\n", " ")
            lines.append(
                f"|{v.rule_id}|{v.file_path}|{v.line}|{v.asil_level.value}"
                f"|{v.severity.value}|{msg}|"
            )
        if len(items) > 50:
            lines.append(f"_…and {len(items) - 50} more (see triage report artifact)._")

        labels = list(self.config.labels) + [
            f"swc-{_slug(swc)}",
            f"misra-{category}",
            f"doors-{_slug(doors_id)}",
        ]
        fields: dict[str, Any] = {
            "project": {"key": self.config.project_key},
            "summary": summary[:255],
            "description": "\n".join(lines),
            "issuetype": {"name": self.config.issue_type},
            "labels": labels,
        }
        # Assignee is best-effort; many instances require accountId instead of email.
        if owner and "@" in owner:
            fields["assignee"] = {"emailAddress": owner}

        return {
            "fields": fields,
            "meta": {
                "swc_module": swc,
                "owner": owner,
                "doors_req_id": doors_id,
                "category": category,
                "violation_count": len(items),
                "fingerprints": [v.fingerprint for v in items],
            },
        }


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")[:40]
