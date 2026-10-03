"""Orchestration service — single entry for the triage pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from misra_triage.baseline.differ import diff_violations
from misra_triage.baseline.store import BaselineStore
from misra_triage.gate.policy import GateDecision, GatePolicy
from misra_triage.jira.client import JiraClient
from misra_triage.jira.ticket_factory import TicketFactory
from misra_triage.mapping.enricher import ViolationEnricher
from misra_triage.models.config import AppConfig
from misra_triage.models.triage_result import TriageReport, TriageSummary
from misra_triage.models.violation import Violation
from misra_triage.parsers.base import ParseError, detect_parser
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)


class TriageService:
    """Coordinates parse → enrich → diff → gate → Jira → report."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.baseline = BaselineStore(config.baseline_path)
        self.enricher = ViolationEnricher(config.mapping)
        self.gate = GatePolicy(config.gate)
        self.jira = JiraClient(config.jira)
        self.tickets = TicketFactory(config.jira)

    def parse_reports(self, report_paths: list[Path]) -> tuple[list[Violation], list[str]]:
        violations: list[Violation] = []
        errors: list[str] = []
        for path in report_paths:
            try:
                parser = detect_parser(path)
                parsed = parser.parse(path)
                if not parsed and not self.config.gate.allow_empty_reports:
                    msg = f"No violations parsed from {path}"
                    logger.warning(msg)
                violations.extend(parsed)
                logger.info("Parsed %d violation(s) from %s via %s", len(parsed), path, parser.__class__.__name__)
            except (ParseError, FileNotFoundError, OSError, ValueError) as exc:
                msg = f"Failed to parse {path}: {exc}"
                logger.error(msg)
                errors.append(msg)
                if self.config.gate.fail_on_parse_errors:
                    raise
        return violations, errors

    def run(
        self,
        report_paths: list[Path],
        *,
        create_tickets: bool = True,
        write_report: bool = True,
    ) -> tuple[TriageReport, GateDecision]:
        if not report_paths:
            raise ValueError("At least one report path is required")

        current, errors = self.parse_reports(report_paths)
        current = self.enricher.enrich_many(current)
        baseline = self.enricher.enrich_many(self.baseline.load())
        diff = diff_violations(current, baseline)
        decision = self.gate.evaluate(diff.new)

        jira_refs: list[dict] = []
        if create_tickets and diff.new:
            payloads = self.tickets.build_issues(diff.new)
            refs = self.jira.create_issues(payloads)
            jira_refs = [
                {
                    "key": r.key,
                    "url": r.url,
                    "dry_run": r.dry_run,
                    "meta": r.meta or {},
                }
                for r in refs
            ]

        tool_sources = sorted({v.tool.value for v in current})
        summary = TriageSummary(
            total=len(current),
            baseline=len(diff.known),
            new=len(diff.new),
            resolved=len(diff.resolved),
            blocking_new=len(decision.blocking),
            tickets_created=len(jira_refs),
            gate_passed=decision.passed,
        )
        report = TriageReport(
            tool_sources=tool_sources,
            summary=summary,
            new_violations=diff.new,
            baseline_violations=diff.known,
            resolved_violations=diff.resolved,
            blocking_violations=decision.blocking,
            jira_issues=jira_refs,
            errors=errors,
        )

        if write_report:
            self._write_report(report)
        return report, decision

    def update_baseline(self, report_paths: list[Path], *, note: str = "") -> int:
        current, errors = self.parse_reports(report_paths)
        if errors and self.config.gate.fail_on_parse_errors:
            raise RuntimeError("; ".join(errors))
        current = self.enricher.enrich_many(current)
        self.baseline.save(current, note=note or "Baseline updated from triage CLI")
        return len(current)

    def _write_report(self, report: TriageReport) -> Path:
        out_dir = self.config.report_output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "triage_report.json"
        path.write_text(
            json.dumps(report.to_dashboard_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logger.info("Wrote triage report to %s", path)
        return path
