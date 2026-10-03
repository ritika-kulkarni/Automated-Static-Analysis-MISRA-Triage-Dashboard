"""Report parsers (Strategy pattern)."""

from misra_triage.parsers.base import ReportParser, detect_parser
from misra_triage.parsers.polyspace_xml import PolyspaceXmlParser
from misra_triage.parsers.qac_xml import QacXmlParser
from misra_triage.parsers.sarif import SarifParser

__all__ = [
    "PolyspaceXmlParser",
    "QacXmlParser",
    "ReportParser",
    "SarifParser",
    "detect_parser",
]
