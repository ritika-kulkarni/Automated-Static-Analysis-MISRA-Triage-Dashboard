"""SARIF 2.1.0 parser (Polyspace Bug Finder / QAC / generic exporters)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from misra_triage.models.violation import ToolSource, Violation
from misra_triage.parsers.base import ParseError, ReportParser, try_load_json
from misra_triage.parsers.rule_catalog import (
    classify_asil,
    classify_misra_category,
    map_severity,
    normalize_rule_id,
)
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)


class SarifParser(ReportParser):
    def can_parse(self, path: Path) -> bool:
        if path.suffix.lower() not in {".sarif", ".json"}:
            return False
        data = try_load_json(path)
        return isinstance(data, dict) and "runs" in data

    def parse(self, path: Path) -> list[Violation]:
        data = try_load_json(path)
        if not isinstance(data, dict) or "runs" not in data:
            raise ParseError(f"Invalid SARIF document: {path}")

        violations: list[Violation] = []
        for run in data.get("runs") or []:
            tool_name = _tool_name(run)
            tool = _map_tool(tool_name)
            rules_by_id = _index_rules(run)
            for result in run.get("results") or []:
                try:
                    violations.append(self._to_violation(result, rules_by_id, tool, tool_name))
                except Exception as exc:  # noqa: BLE001 - isolate bad rows
                    logger.warning("Skipping malformed SARIF result in %s: %s", path.name, exc)
        if not violations:
            logger.warning("SARIF report contained zero parseable results: %s", path)
        return violations

    def _to_violation(
        self,
        result: dict[str, Any],
        rules_by_id: dict[str, dict[str, Any]],
        tool: ToolSource,
        tool_name: str,
    ) -> Violation:
        raw_rule = result.get("ruleId")
        if raw_rule is None or str(raw_rule).strip() in {"", "None", "null"}:
            raise ValueError("SARIF result missing ruleId")
        rule_id = normalize_rule_id(str(raw_rule))
        if not rule_id or rule_id == "unknown":
            raise ValueError(f"SARIF result has unusable ruleId: {raw_rule!r}")
        message = _extract_message(result)
        file_path, line, column = _extract_location(result)
        rule_meta = rules_by_id.get(rule_id) or rules_by_id.get(str(result.get("ruleId") or ""))
        level = str(result.get("level") or (rule_meta or {}).get("defaultConfiguration", {}).get("level") or "")
        properties = {
            **((rule_meta or {}).get("properties") or {}),
            **(result.get("properties") or {}),
        }
        category_hint = str(properties.get("category") or properties.get("kind") or "")
        asil_text = " ".join(
            str(properties.get(k, "")) for k in ("asil", "ASIL", "safetyIntegrityLevel", "tags")
        )
        tags = properties.get("tags")
        if isinstance(tags, list):
            asil_text = f"{asil_text} {' '.join(str(t) for t in tags)}"

        return Violation(
            rule_id=rule_id,
            message=message,
            file_path=file_path or "unknown",
            line=line,
            column=column,
            severity=map_severity(level),
            misra_category=classify_misra_category(rule_id, message, category_hint),
            asil_level=classify_asil(asil_text or f"{message} {tool_name}"),
            tool=tool,
            raw={"tool": tool_name, "level": level, "properties": properties},
        )


def _tool_name(run: dict[str, Any]) -> str:
    driver = ((run.get("tool") or {}).get("driver") or {})
    return str(driver.get("name") or driver.get("fullName") or "sarif")


def _map_tool(name: str) -> ToolSource:
    lowered = name.lower()
    if "polyspace" in lowered or "bug finder" in lowered:
        return ToolSource.POLYSPACE
    if "qac" in lowered or "helixa" in lowered or "perforce" in lowered:
        return ToolSource.QAC
    return ToolSource.SARIF


def _index_rules(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    driver = ((run.get("tool") or {}).get("driver") or {})
    indexed: dict[str, dict[str, Any]] = {}
    for rule in driver.get("rules") or []:
        rid = str(rule.get("id") or "")
        if rid:
            indexed[rid] = rule
            indexed[normalize_rule_id(rid)] = rule
    return indexed


def _extract_message(result: dict[str, Any]) -> str:
    message = result.get("message") or {}
    if isinstance(message, dict):
        return str(message.get("text") or message.get("markdown") or "")
    return str(message)


def _extract_location(result: dict[str, Any]) -> tuple[str, int, int]:
    locations = result.get("locations") or []
    if not locations:
        return "unknown", 0, 0
    physical = ((locations[0] or {}).get("physicalLocation") or {})
    artifact = physical.get("artifactLocation") or {}
    region = physical.get("region") or {}
    uri = str(artifact.get("uri") or artifact.get("uriBaseId") or "unknown")
    line = int(region.get("startLine") or 0)
    column = int(region.get("startColumn") or 0)
    return uri, line, column
