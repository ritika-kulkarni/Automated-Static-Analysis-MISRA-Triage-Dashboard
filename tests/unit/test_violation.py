"""Unit tests for the Violation domain model."""

from misra_triage.models.violation import (
    AsilLevel,
    MisraCategory,
    Violation,
    ViolationSeverity,
)


def test_fingerprint_stable_and_path_normalized():
    a = Violation(
        rule_id="Rule-9.1",
        message="Hello   World",
        file_path="./Src/App/BrakeCtrl.c",
        line=10,
        column=2,
    )
    b = Violation(
        rule_id="rule-9.1",
        message="hello world",
        file_path="src/app/brakectrl.c",
        line=10,
        column=2,
    )
    assert a.fingerprint == b.fingerprint


def test_fingerprint_changes_with_line():
    a = Violation(rule_id="rule-1.1", message="x", file_path="a.c", line=1)
    b = Violation(rule_id="rule-1.1", message="x", file_path="a.c", line=2)
    assert a.fingerprint != b.fingerprint


def test_is_blocking_mandatory_or_asil_critical():
    mandatory = Violation(
        rule_id="rule-9.1",
        file_path="a.c",
        misra_category=MisraCategory.MANDATORY,
        asil_level=AsilLevel.A,
    )
    asil_d = Violation(
        rule_id="rule-8.4",
        file_path="a.c",
        misra_category=MisraCategory.REQUIRED,
        asil_level=AsilLevel.D,
        severity=ViolationSeverity.HIGH,
    )
    advisory = Violation(
        rule_id="rule-2.2",
        file_path="a.c",
        misra_category=MisraCategory.ADVISORY,
        asil_level=AsilLevel.A,
    )
    assert mandatory.is_blocking is True
    assert asil_d.is_blocking is True
    assert advisory.is_blocking is False
