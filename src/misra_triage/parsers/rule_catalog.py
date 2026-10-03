"""Heuristics to classify MISRA category / ASIL from rule identifiers."""

from __future__ import annotations

import re

from misra_triage.models.violation import AsilLevel, MisraCategory, ViolationSeverity

# Common MISRA C:2012 Mandatory directives / rules (representative set).
# Extensible via config overlays in production deployments.
_MANDATORY_RULES = {
    "dir-4.1",
    "dir-4.3",
    "dir-4.7",
    "dir-4.11",
    "dir-4.12",
    "rule-1.1",
    "rule-1.3",
    "rule-3.1",
    "rule-3.2",
    "rule-4.1",
    "rule-4.2",
    "rule-8.1",
    "rule-8.14",
    "rule-9.1",
    "rule-12.5",
    "rule-13.6",
    "rule-17.3",
    "rule-17.4",
    "rule-17.6",
    "rule-19.1",
    "rule-21.3",
    "rule-21.13",
    "rule-21.17",
    "rule-21.18",
    "rule-21.19",
    "rule-21.20",
    "rule-22.2",
    "rule-22.4",
    "rule-22.5",
    "rule-22.6",
}

_REQUIRED_HINT = re.compile(r"(required|misra[-_ ]?c[: ]?2012)", re.I)
_MANDATORY_HINT = re.compile(r"mandatory", re.I)
_ADVISORY_HINT = re.compile(r"advisory", re.I)
_RULE_ID_NORM = re.compile(r"(dir|rule)[-_\s]?(\d+)[.\-](\d+)", re.I)
_ASIL_HINT = re.compile(r"\basil[-_ ]?([abcd]|qm)\b", re.I)


def normalize_rule_id(rule_id: str) -> str:
    match = _RULE_ID_NORM.search(rule_id or "")
    if match:
        return f"{match.group(1).lower()}-{match.group(2)}.{match.group(3)}"
    return (rule_id or "").strip().lower()


def classify_misra_category(rule_id: str, message: str = "", level_hint: str = "") -> MisraCategory:
    text = f"{rule_id} {message} {level_hint}"
    if _MANDATORY_HINT.search(text):
        return MisraCategory.MANDATORY
    if _ADVISORY_HINT.search(text):
        return MisraCategory.ADVISORY
    if _REQUIRED_HINT.search(text):
        return MisraCategory.REQUIRED

    normalized = normalize_rule_id(rule_id)
    if normalized in _MANDATORY_RULES:
        return MisraCategory.MANDATORY
    if normalized.startswith(("dir-", "rule-")):
        return MisraCategory.REQUIRED
    return MisraCategory.UNKNOWN


def classify_asil(text: str, default: AsilLevel = AsilLevel.UNKNOWN) -> AsilLevel:
    match = _ASIL_HINT.search(text or "")
    if not match:
        return default
    token = match.group(1).upper()
    return AsilLevel.QM if token == "QM" else AsilLevel[token]


def map_severity(raw: str | None) -> ViolationSeverity:
    if not raw:
        return ViolationSeverity.UNKNOWN
    token = raw.strip().lower()
    mapping = {
        "error": ViolationSeverity.CRITICAL,
        "critical": ViolationSeverity.CRITICAL,
        "fatal": ViolationSeverity.CRITICAL,
        "high": ViolationSeverity.HIGH,
        "warning": ViolationSeverity.HIGH,
        "medium": ViolationSeverity.MEDIUM,
        "note": ViolationSeverity.LOW,
        "low": ViolationSeverity.LOW,
        "info": ViolationSeverity.INFO,
        "recommendation": ViolationSeverity.INFO,
    }
    return mapping.get(token, ViolationSeverity.UNKNOWN)
