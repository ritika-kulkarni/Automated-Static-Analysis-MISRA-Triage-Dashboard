"""Helix QAC / PRQA XML report parser."""

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

_QAC_ROOTS = {"QAC", "PRQA", "Results", "DiagnosticList", "HelixQAC"}


class QacXmlParser(ReportParser):
    def can_parse(self, path: Path) -> bool:
        if path.suffix.lower() != ".xml":
            return False
        # Prefer explicit naming when both Polyspace and QAC use .xml
        if "qac" in path.name.lower() or "prqa" in path.name.lower():
            return True
        root = try_load_xml(path)
        if root is None:
            return False
        tag = _local(root.tag)
        if tag in _QAC_ROOTS:
            return True
        return root.find(".//Diagnostic") is not None or root.find(".//Message") is not None

    def parse(self, path: Path) -> list[Violation]:
        root = try_load_xml(path)
        if root is None:
            raise ParseError(f"Invalid QAC XML: {path}")

        violations: list[Violation] = []
        for node in root.iter():
            tag = _local(node.tag).lower()
            if tag not in {"diagnostic", "message", "violation", "warning"}:
                continue
            try:
                violation = self._to_violation(node)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed QAC node in %s: %s", path.name, exc)
                continue
            if violation is not None:
                violations.append(violation)

        if not violations:
            logger.warning("QAC XML contained zero parseable findings: %s", path)
        return violations

    def _to_violation(self, node: ET.Element) -> Violation | None:
        rule_id = (
            node.attrib.get("msg")
            or node.attrib.get("rule")
            or node.attrib.get("code")
            or node.attrib.get("id")
            or _child_text(node, "Rule")
            or _child_text(node, "Code")
        )
        if not rule_id:
            return None

        message = (
            node.attrib.get("text")
            or node.attrib.get("message")
            or _child_text(node, "Text")
            or _child_text(node, "Message")
            or (node.text or "").strip()
        )
        file_path = (
            node.attrib.get("file")
            or node.attrib.get("filename")
            or _child_text(node, "File")
            or "unknown"
        )
        line = _to_int(node.attrib.get("line") or _child_text(node, "Line"))
        column = _to_int(node.attrib.get("col") or node.attrib.get("column") or _child_text(node, "Column"))
        severity = node.attrib.get("severity") or node.attrib.get("level") or _child_text(node, "Severity")
        category = node.attrib.get("category") or node.attrib.get("group") or ""
        asil_text = node.attrib.get("asil") or f"{message} {category}"
        rule_norm = normalize_rule_id(str(rule_id))

        return Violation(
            rule_id=rule_norm or str(rule_id),
            message=message,
            file_path=file_path,
            line=line,
            column=column,
            severity=map_severity(severity),
            misra_category=classify_misra_category(rule_norm or str(rule_id), message, category),
            asil_level=classify_asil(asil_text),
            tool=ToolSource.QAC,
            raw={"tag": _local(node.tag), "attrib": dict(node.attrib)},
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
