"""Polyspace Bug Finder XML report parser."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from misra_triage.models.violation import ToolSource, Violation
from misra_triage.parsers.base import ParseError, ReportParser, try_load_xml
from misra_triage.parsers.rule_catalog import (
    classify_asil,
    classify_misra_category,
    map_severity,
    normalize_rule_id,
)
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)

_POLYSPACE_ROOTS = {"BugFinderResults", "Results", "PolyspaceBugFinderResults"}


class PolyspaceXmlParser(ReportParser):
    def can_parse(self, path: Path) -> bool:
        if path.suffix.lower() != ".xml":
            return False
        root = try_load_xml(path)
        if root is None:
            return False
        tag = _local(root.tag)
        if tag in _POLYSPACE_ROOTS:
            return True
        # Heuristic: Polyspace exports often include Check / Color attributes.
        return root.find(".//Check") is not None or "polyspace" in path.name.lower()

    def parse(self, path: Path) -> list[Violation]:
        root = try_load_xml(path)
        if root is None:
            raise ParseError(f"Invalid Polyspace XML: {path}")

        violations: list[Violation] = []
        checks = list(root.iter())
        for node in checks:
            if _local(node.tag) not in {"Check", "Result", "Defect", "Finding"}:
                continue
            try:
                violation = self._node_to_violation(node)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed Polyspace node in %s: %s", path.name, exc)
                continue
            if violation is not None:
                violations.append(violation)

        if not violations:
            # Fallback: nested <violation> style used by some exporters.
            for node in root.iter():
                if _local(node.tag).lower() == "violation":
                    try:
                        violations.append(self._generic_violation(node))
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Skipping Polyspace <violation>: %s", exc)

        if not violations:
            logger.warning("Polyspace XML contained zero parseable findings: %s", path)
        return violations

    def _node_to_violation(self, node: ET.Element) -> Violation | None:
        rule_id = (
            node.attrib.get("check")
            or node.attrib.get("rule")
            or node.attrib.get("id")
            or _child_text(node, "Rule")
            or _child_text(node, "Check")
        )
        if not rule_id:
            return None
        message = (
            node.attrib.get("msg")
            or node.attrib.get("message")
            or _child_text(node, "Message")
            or _child_text(node, "Description")
            or ""
        )
        file_path = (
            node.attrib.get("file")
            or _child_text(node, "File")
            or _child_text(node, "FileName")
            or "unknown"
        )
        line = _to_int(node.attrib.get("line") or _child_text(node, "Line"))
        column = _to_int(node.attrib.get("col") or node.attrib.get("column") or _child_text(node, "Column"))
        color = node.attrib.get("color") or node.attrib.get("severity") or _child_text(node, "Severity") or ""
        category = node.attrib.get("category") or _child_text(node, "Category") or ""
        asil_text = (
            node.attrib.get("asil")
            or _child_text(node, "ASIL")
            or f"{message} {category}"
        )
        rule_norm = normalize_rule_id(rule_id)
        return Violation(
            rule_id=rule_norm,
            message=message,
            file_path=file_path,
            line=line,
            column=column,
            severity=map_severity(color),
            misra_category=classify_misra_category(rule_norm, message, category),
            asil_level=classify_asil(asil_text),
            tool=ToolSource.POLYSPACE,
            raw={"tag": _local(node.tag), "attrib": dict(node.attrib)},
        )

    def _generic_violation(self, node: ET.Element) -> Violation:
        rule_id = normalize_rule_id(node.attrib.get("ruleId") or node.attrib.get("rule") or "unknown")
        message = node.attrib.get("message") or (node.text or "")
        return Violation(
            rule_id=rule_id,
            message=message.strip(),
            file_path=node.attrib.get("file") or "unknown",
            line=_to_int(node.attrib.get("line")),
            column=_to_int(node.attrib.get("column")),
            severity=map_severity(node.attrib.get("severity")),
            misra_category=classify_misra_category(rule_id, message, node.attrib.get("category", "")),
            asil_level=classify_asil(node.attrib.get("asil", "")),
            tool=ToolSource.POLYSPACE,
            raw={"attrib": dict(node.attrib)},
        )


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _child_text(node: ET.Element, name: str) -> str | None:
    for child in list(node):
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _to_int(value: str | None) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0
