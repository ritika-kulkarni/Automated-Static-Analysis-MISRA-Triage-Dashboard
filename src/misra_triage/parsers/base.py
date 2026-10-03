"""Parser abstraction and format auto-detection."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from xml.etree import ElementTree as ET

from misra_triage.models.violation import Violation
from misra_triage.utils.logging import get_logger

logger = get_logger(__name__)


class ParseError(ValueError):
    """Raised when a report cannot be parsed into violations."""


class ReportParser(ABC):
    """Strategy interface for tool-specific report formats."""

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, path: Path) -> list[Violation]:
        raise NotImplementedError


def detect_parser(path: Path, parsers: list[ReportParser] | None = None) -> ReportParser:
    """Pick the first parser that claims support for *path*."""
    from misra_triage.parsers.polyspace_xml import PolyspaceXmlParser
    from misra_triage.parsers.qac_xml import QacXmlParser
    from misra_triage.parsers.sarif import SarifParser

    candidates = parsers or [SarifParser(), PolyspaceXmlParser(), QacXmlParser()]
    for parser in candidates:
        try:
            if parser.can_parse(path):
                logger.debug("Selected parser %s for %s", parser.__class__.__name__, path)
                return parser
        except OSError as exc:
            logger.warning("Parser probe failed for %s: %s", path, exc)
    raise ParseError(f"No parser available for report: {path}")


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {path}")
    if path.stat().st_size == 0:
        raise ParseError(f"Report is empty: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def try_load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(read_text(path))
    except (json.JSONDecodeError, FileNotFoundError, ParseError):
        return None


def try_load_xml(path: Path) -> ET.Element | None:
    try:
        return ET.fromstring(read_text(path))
    except (ET.ParseError, FileNotFoundError, ParseError, OSError):
        return None
