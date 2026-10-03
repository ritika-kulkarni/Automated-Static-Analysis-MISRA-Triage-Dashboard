"""Shared fixtures for unit and integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from misra_triage.models.config import AppConfig, GatePolicyConfig, JiraConfig, MappingConfig
from misra_triage.models.violation import (
    AsilLevel,
    MisraCategory,
    ToolSource,
    Violation,
    ViolationSeverity,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


@pytest.fixture
def samples_dir() -> Path:
    return SAMPLES


@pytest.fixture
def tmp_config(tmp_path: Path) -> AppConfig:
    owner_map = tmp_path / "owner_map.yaml"
    doors_map = tmp_path / "doors_map.yaml"
    owner_map.write_text(
        yaml.dump(
            {
                "mappings": [
                    {
                        "prefix": "src/bsw/can",
                        "swc": "CanIf",
                        "owner": "team-can@example.com",
                        "asil": "B",
                    },
                    {
                        "prefix": "src/bsw/nvm",
                        "swc": "NvM",
                        "owner": "team-mem@example.com",
                        "asil": "C",
                    },
                    {
                        "prefix": "src/app/brake",
                        "swc": "BrakeCtrl",
                        "owner": "team-chassis@example.com",
                        "asil": "D",
                    },
                    {
                        "prefix": "src/app/hmi",
                        "swc": "HmiMgr",
                        "owner": "team-hmi@example.com",
                        "asil": "A",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    doors_map.write_text(
        yaml.dump(
            {
                "mappings": [
                    {"prefix": "src/bsw/can", "doors_id": "REQ-CAN-001"},
                    {"prefix": "src/bsw/nvm", "doors_id": "REQ-NVM-014"},
                    {"prefix": "src/app/brake", "doors_id": "REQ-BRK-003"},
                    {"prefix": "src/app/hmi", "doors_id": "REQ-HMI-022"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return AppConfig(
        baseline_path=tmp_path / "baseline" / "violations.json",
        report_output_dir=tmp_path / "reports",
        gate=GatePolicyConfig(),
        jira=JiraConfig(
            enabled=True,
            dry_run=True,
            base_url="https://jira.example.com",
            project_key="SWQ",
        ),
        mapping=MappingConfig(
            owner_map_path=owner_map,
            doors_map_path=doors_map,
            default_owner="unassigned",
        ),
        log_level="WARNING",
    )


@pytest.fixture
def sample_violation() -> Violation:
    return Violation(
        rule_id="rule-9.1",
        message="Uninitialized automatic object",
        file_path="src/app/brake/BrakeCtrl.c",
        line=42,
        column=5,
        severity=ViolationSeverity.CRITICAL,
        misra_category=MisraCategory.MANDATORY,
        asil_level=AsilLevel.D,
        tool=ToolSource.POLYSPACE,
    )
