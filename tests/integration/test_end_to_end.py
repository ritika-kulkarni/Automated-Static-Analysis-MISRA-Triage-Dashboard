"""End-to-end workflow tests against sample Polyspace/QAC reports."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from misra_triage.cli import main
from misra_triage.service import TriageService


@pytest.mark.integration
def test_full_triage_blocks_on_new_mandatory(tmp_config, samples_dir: Path):
    service = TriageService(tmp_config)
    reports = [
        samples_dir / "polyspace_bugfinder.sarif",
        samples_dir / "qac_report.xml",
        samples_dir / "polyspace_results.xml",
    ]

    # First drop establishes baseline (accept all current debt).
    count = service.update_baseline(reports, note="initial debt")
    assert count > 0

    # Same reports again → no new findings → gate passes.
    report, decision = service.run(reports, create_tickets=True)
    assert decision.passed is True
    assert report.summary.new == 0
    assert report.summary.gate_passed is True

    # Inject a brand-new mandatory finding into a synthetic SARIF.
    new_sarif = tmp_config.report_output_dir.parent / "new.sarif"
    new_sarif.write_text(
        """
{
  "version": "2.1.0",
  "runs": [{
    "tool": {"driver": {"name": "Polyspace Bug Finder", "rules": []}},
    "results": [{
      "ruleId": "MISRA C:2012 Rule-9.1",
      "level": "error",
      "message": {"text": "Uninitialized object (Mandatory)."},
      "locations": [{
        "physicalLocation": {
          "artifactLocation": {"uri": "src/app/brake/NewFile.c"},
          "region": {"startLine": 7, "startColumn": 1}
        }
      }],
      "properties": {"tags": ["ASIL-D"]}
    }]
  }]
}
""".strip(),
        encoding="utf-8",
    )

    report2, decision2 = service.run(reports + [new_sarif], create_tickets=True)
    assert decision2.passed is False
    assert report2.summary.blocking_new >= 1
    assert report2.summary.tickets_created >= 1
    assert (tmp_config.report_output_dir / "triage_report.json").exists()


@pytest.mark.integration
def test_cli_triage_and_update_baseline(tmp_path, samples_dir: Path, tmp_config):
    # Persist config to disk for CLI.
    import yaml

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "baseline_path": str(tmp_config.baseline_path),
                "report_output_dir": str(tmp_config.report_output_dir),
                "log_level": "WARNING",
                "gate": {"fail_on_parse_errors": True, "allow_empty_reports": True},
                "jira": {
                    "enabled": True,
                    "dry_run": True,
                    "base_url": "https://jira.example.com",
                    "project_key": "SWQ",
                },
                "mapping": {
                    "owner_map_path": str(tmp_config.mapping.owner_map_path),
                    "doors_map_path": str(tmp_config.mapping.doors_map_path),
                    "default_owner": "unassigned",
                },
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    baseline_result = runner.invoke(
        main,
        [
            "update-baseline",
            "--config",
            str(config_path),
            "--report",
            str(samples_dir / "polyspace_bugfinder.sarif"),
        ],
    )
    assert baseline_result.exit_code == 0, baseline_result.output

    triage_result = runner.invoke(
        main,
        [
            "triage",
            "--config",
            str(config_path),
            "--report",
            str(samples_dir / "polyspace_bugfinder.sarif"),
            "--json-out",
        ],
    )
    assert triage_result.exit_code == 0, triage_result.output
    assert '"gate_passed": true' in triage_result.output.lower() or '"gate_passed": true' in triage_result.output
