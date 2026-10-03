from pathlib import Path

import pytest

from misra_triage.models.violation import MisraCategory, ToolSource
from misra_triage.parsers.base import ParseError, detect_parser
from misra_triage.parsers.polyspace_xml import PolyspaceXmlParser
from misra_triage.parsers.qac_xml import QacXmlParser
from misra_triage.parsers.sarif import SarifParser


def test_sarif_parser(samples_dir: Path):
    path = samples_dir / "polyspace_bugfinder.sarif"
    parser = SarifParser()
    assert parser.can_parse(path)
    violations = parser.parse(path)
    assert len(violations) == 3
    assert all(v.tool == ToolSource.POLYSPACE for v in violations)
    mandatory = [v for v in violations if v.misra_category == MisraCategory.MANDATORY]
    assert len(mandatory) >= 2


def test_polyspace_xml_parser(samples_dir: Path):
    path = samples_dir / "polyspace_results.xml"
    parser = PolyspaceXmlParser()
    assert parser.can_parse(path)
    violations = parser.parse(path)
    assert len(violations) == 3
    assert any(v.rule_id == "rule-17.3" for v in violations)


def test_qac_xml_parser(samples_dir: Path):
    path = samples_dir / "qac_report.xml"
    parser = QacXmlParser()
    assert parser.can_parse(path)
    violations = parser.parse(path)
    assert len(violations) == 3
    assert all(v.tool == ToolSource.QAC for v in violations)


def test_detect_parser_selects_correct_strategy(samples_dir: Path):
    assert isinstance(detect_parser(samples_dir / "polyspace_bugfinder.sarif"), SarifParser)
    assert isinstance(detect_parser(samples_dir / "qac_report.xml"), QacXmlParser)
    assert isinstance(detect_parser(samples_dir / "polyspace_results.xml"), PolyspaceXmlParser)


def test_empty_report_raises(tmp_path: Path):
    empty = tmp_path / "empty.sarif"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ParseError):
        SarifParser().parse(empty)


def test_malformed_sarif_raises(tmp_path: Path):
    bad = tmp_path / "bad.sarif"
    bad.write_text('{"version":"2.1.0"}', encoding="utf-8")
    with pytest.raises(ParseError):
        SarifParser().parse(bad)
