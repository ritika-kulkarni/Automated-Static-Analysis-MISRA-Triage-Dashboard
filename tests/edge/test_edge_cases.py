"""Edge-case and resilience validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from misra_triage.baseline.store import BaselineStore
from misra_triage.models.config import load_config
from misra_triage.models.violation import Violation
from misra_triage.parsers.base import ParseError, detect_parser
from misra_triage.parsers.sarif import SarifParser
from misra_triage.service import TriageService


@pytest.mark.edge
def test_corrupt_baseline_raises(tmp_path: Path):
    path = tmp_path / "baseline.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupt baseline"):
        BaselineStore(path).load()


@pytest.mark.edge
def test_baseline_skips_invalid_entries(tmp_path: Path):
    path = tmp_path / "baseline.json"
    path.write_text(
        '{"violations": [{"rule_id": "rule-1.1", "file_path": "a.c"}, {"bad": true}]}',
        encoding="utf-8",
    )
    loaded = BaselineStore(path).load()
    assert len(loaded) == 1


@pytest.mark.edge
def test_sarif_skips_malformed_result_rows(tmp_path: Path):
    path = tmp_path / "partial.sarif"
    path.write_text(
        """
{
  "version": "2.1.0",
  "runs": [{
    "tool": {"driver": {"name": "Polyspace Bug Finder"}},
    "results": [
      {"ruleId": null},
      {
        "ruleId": "Rule-8.4",
        "message": {"text": "ok"},
        "locations": [{
          "physicalLocation": {
            "artifactLocation": {"uri": "src/bsw/can/CanIf.c"},
            "region": {"startLine": 1}
          }
        }]
      }
    ]
  }]
}
""".strip(),
        encoding="utf-8",
    )
    violations = SarifParser().parse(path)
    assert len(violations) == 1


@pytest.mark.edge
def test_unknown_format_raises(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(ParseError):
        detect_parser(path)


@pytest.mark.edge
def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))


@pytest.mark.edge
def test_empty_report_list_rejected(tmp_config):
    service = TriageService(tmp_config)
    with pytest.raises(ValueError, match="At least one report"):
        service.run([])


@pytest.mark.edge
def test_duplicate_fingerprints_collapse_in_diff():
    from misra_triage.baseline.differ import diff_violations

    a = Violation(rule_id="rule-1.1", file_path="a.c", line=1, message="x")
    b = Violation(rule_id="rule-1.1", file_path="a.c", line=1, message="x")
    diff = diff_violations([a, b], [])
    # dict keyed by fingerprint keeps one of the duplicates as "new"
    assert len(diff.new) == 1


@pytest.mark.edge
def test_parse_error_propagates_when_configured(tmp_config, tmp_path: Path):
    tmp_config.gate.fail_on_parse_errors = True
    service = TriageService(tmp_config)
    bad = tmp_path / "bad.xml"
    bad.write_text("<not><closed>", encoding="utf-8")
    with pytest.raises((ParseError, Exception)):
        service.parse_reports([bad])
